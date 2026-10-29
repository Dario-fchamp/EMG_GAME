"""Input layer: the game only consumes Commands, never raw keys (except for name entry).

KeyboardSource: arrows / A D / SPACE / P / ESC.
OscSource: LEFT/RIGHT sent by Bonsai over OSC (UDP), received on a background thread.
"""
import queue
import select
import socket
import struct
import threading
from enum import Enum, auto

import pygame

import config as C
import osc_protocol


class Command(Enum):
    LEFT = auto()       # from keyboard, or from EMG via Bonsai (OSC)
    RIGHT = auto()
    START = auto()      # START/PAUSE/BACK/QUIT: keyboard (and window close) only
    PAUSE = auto()
    BACK = auto()
    QUIT = auto()


class CommandSource:
    def start(self):
        pass

    def poll(self, pygame_events):
        """Return all commands received since the last call, without blocking."""
        raise NotImplementedError

    def stop(self):
        pass


class KeyboardSource(CommandSource):
    def __init__(self, osc_mode=False):
        self._keymap = (
            (C.KEYS_LEFT_OSC if osc_mode else C.KEYS_LEFT, Command.LEFT),
            (C.KEYS_RIGHT_OSC if osc_mode else C.KEYS_RIGHT, Command.RIGHT),
            (C.KEYS_START, Command.START),
            (C.KEYS_PAUSE, Command.PAUSE),
            (C.KEYS_BACK, Command.BACK),
        )

    def poll(self, pygame_events):
        out = []
        for e in pygame_events:
            if e.type == pygame.KEYDOWN:    # KEYDOWN only -> holding a key = one command
                for keys, cmd in self._keymap:
                    if e.key in keys:
                        out.append(cmd)
                        break
            elif e.type == pygame.QUIT:     # window close button
                out.append(Command.QUIT)
        return out


def _number(value):
    """OSC argument as a float (bools -> 0/1), or None if not numeric."""
    if isinstance(value, (bool, int, float)):
        return float(value)
    return None


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _key_code(name):
    """Windows key code of a key name: letters and digits use their ASCII code (A = 65)."""
    name = name.strip().upper()
    return ord(name) if len(name) == 1 else None


class OscSource(CommandSource):
    """Receives OSC messages from Bonsai and turns them into LEFT/RIGHT commands.

    Main address OSC_ADDRESS_PAIR, two kinds of messages:
        PAIR  exactly two numbers/bools ("ii", "ff", "TF"), from Zip/CombineLatest(left, right):
              Item1 = LEFT channel, Item2 = RIGHT. Each channel gives ONE command when it goes
              inactive -> active (rising edge, ON/OFF thresholds): every sample or only changes both work.
        KEY   anything else, e.g. from KeyDown -> SendMessage: one command per message if it contains
              the OSC_KEY_LEFT / OSC_KEY_RIGHT key (key code like 65, name like "A"), or LEFT/RIGHT, 1/2.
    Also accepted (single value):
        OSC_ADDRESS_CMD    int 1 -> LEFT, 2 -> RIGHT (0 ignored), or string "LEFT"/"RIGHT"
        OSC_ADDRESS_LEFT   true / non-zero value, or no argument -> LEFT  (false / 0 ignored)
        OSC_ADDRESS_RIGHT  same -> RIGHT
    Menus stay keyboard-only: nothing received over OSC can start, pause or quit the game.
    """

    def __init__(self, host=C.OSC_HOST, port=C.OSC_PORT, trigger=C.OSC_TRIGGER):
        self.host, self.port, self.trigger = host, port, trigger
        self.queue = queue.Queue()
        self.socks = []
        self.thread = None
        self.running = False
        self.ok = False
        self.status = f"OSC {host}:{port} - not started"
        # diagnostics, read by the menu
        self.n_commands = 0
        self.last_command = None
        self.n_messages = 0
        self.last_message = None            # (address, args) of the last message received
        self._pair_active = [False, False]  # LEFT / RIGHT channel state, for rising-edge detection
        self._last_active = {}              # address -> last Command/None, for trigger == "rising"
        self._warned = set()

    # ---------- sockets / thread ----------
    def start(self):
        try:
            self.socks.append(self._bind(socket.AF_INET, self.host))
        except OSError as e:
            self.status = f"OSC ERROR: port {self.port} in use"
            print(f"Warning: cannot listen on {self.host}:{self.port} ({e.strerror or e}).\n"
                  f"  Another program uses this port: is the Bonsai 'UdpReceive' CreateUdpClient "
                  f"(Port = {self.port}) running, or another game instance? Keyboard still works.")
            return
        if C.OSC_LISTEN_IPV6 and self.host in ("127.0.0.1", "localhost") and socket.has_ipv6:
            try:                            # in case Bonsai's "localhost" resolves to ::1
                self.socks.append(self._bind(socket.AF_INET6, "::1"))
            except OSError:
                pass                        # optional
        self.running = True
        self.ok = True
        self.status = f"OSC listening on port {self.port}"
        self.thread = threading.Thread(target=self._listen, name="OscSource", daemon=True)
        self.thread.start()

    def _bind(self, family, host):
        sock = socket.socket(family, socket.SOCK_DGRAM)
        try:
            sock.bind((host, self.port))
        except OSError:
            sock.close()
            raise
        return sock

    def _warn_once(self, key, msg):
        if key not in self._warned:
            self._warned.add(key)
            print(f"Warning: {msg}")

    def _listen(self):
        while self.running:
            try:
                readable, _, _ = select.select(self.socks, [], [], 0.2)   # timeout lets stop() work
            except (OSError, ValueError):   # sockets closed by stop()
                break
            for sock in readable:
                try:
                    data, _ = sock.recvfrom(65535)
                except ConnectionResetError:    # Windows quirk on UDP sockets; harmless
                    continue
                except OSError:
                    return
                try:
                    messages = osc_protocol.parse_packet(data)
                except (ValueError, struct.error, IndexError) as e:
                    self._warn_once("malformed", f"ignoring malformed OSC packet ({e})")
                    continue
                for address, args in messages:
                    self._handle(address, args)

    # ---------- message -> command ----------
    def _emit(self, cmd):
        self.n_commands += 1
        self.last_command = cmd
        self.queue.put(cmd)

    def _handle_main(self, args):
        if len(args) == 2 and all(_number(a) is not None for a in args):
            self._handle_pair(args)
            return
        cmd = self._key_command(args)
        if cmd is None:
            self._warn_once(("main", len(args)),
                            f"{C.OSC_ADDRESS_PAIR} message not understood: {args!r}. Expected 2 values "
                            f"(left, right), or a key {C.OSC_KEY_LEFT}/{C.OSC_KEY_RIGHT}.")
            return
        self._emit(cmd)                     # one key press = one command

    def _key_command(self, args):
        """Find the LEFT/RIGHT key in a KeyDown message, whatever way Bonsai serialized the key."""
        names = {C.OSC_KEY_LEFT.upper(): Command.LEFT, C.OSC_KEY_RIGHT.upper(): Command.RIGHT,
                 "LEFT": Command.LEFT, "RIGHT": Command.RIGHT}
        codes = {_key_code(C.OSC_KEY_LEFT): Command.LEFT, _key_code(C.OSC_KEY_RIGHT): Command.RIGHT}
        if len(args) == 1 and _is_int(args[0]) and args[0] in (1, 2):
            return Command.LEFT if args[0] == 1 else Command.RIGHT
        for a in args:
            if isinstance(a, str) and a.strip().upper() in names:
                return names[a.strip().upper()]
            if _is_int(a) and a in codes:
                return codes[a]
        return None

    def _handle_pair(self, args):
        for i, cmd in enumerate((Command.LEFT, Command.RIGHT)):
            value = _number(args[i])
            if not self._pair_active[i] and value > C.OSC_PAIR_THRESHOLD_ON:
                self._pair_active[i] = True
                self._emit(cmd)             # rising edge = one contraction = one command
            elif self._pair_active[i] and value <= C.OSC_PAIR_THRESHOLD_OFF:
                self._pair_active[i] = False

    def _single_command(self, address, args):
        value = args[0] if args else True   # no argument (impulse) = active
        if address == C.OSC_ADDRESS_CMD:
            if isinstance(value, str):
                return {"LEFT": Command.LEFT, "RIGHT": Command.RIGHT}.get(value.strip().upper())
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return {1: Command.LEFT, 2: Command.RIGHT}.get(int(value))
            return None
        if address == C.OSC_ADDRESS_LEFT:
            return Command.LEFT if value else None
        return Command.RIGHT if value else None     # OSC_ADDRESS_RIGHT

    def _handle(self, address, args):
        self.n_messages += 1
        self.last_message = (address, args)
        signature = (address, tuple(type(a).__name__ for a in args))
        if signature not in self._warned:   # shows what Bonsai really sends (helps debugging)
            self._warned.add(signature)
            print(f"OSC: first message of this kind: {address} {args!r}")
        if address == C.OSC_ADDRESS_PAIR:
            self._handle_main(args)
            return
        if address not in (C.OSC_ADDRESS_CMD, C.OSC_ADDRESS_LEFT, C.OSC_ADDRESS_RIGHT):
            self._warn_once(address, f"ignoring OSC address {address!r} (expected {C.OSC_ADDRESS_PAIR}, "
                                     f"{C.OSC_ADDRESS_CMD}, {C.OSC_ADDRESS_LEFT} or {C.OSC_ADDRESS_RIGHT})")
            return
        cmd = self._single_command(address, args)
        if self.trigger == "rising":
            previous = self._last_active.get(address)
            self._last_active[address] = cmd
            if cmd == previous:
                return
        if cmd is not None:
            self._emit(cmd)

    # ---------- CommandSource ----------
    def poll(self, pygame_events):
        out = []
        while True:
            try:
                out.append(self.queue.get_nowait())
            except queue.Empty:
                return out

    def stop(self):
        self.running = False
        for sock in self.socks:
            sock.close()
        if self.thread is not None:
            self.thread.join(timeout=1)
