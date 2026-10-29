"""Input layer: the game only consumes Commands, never raw keys (except for name entry).

KeyboardSource: arrows / A D / SPACE / P / ESC.
OscSource: LEFT/RIGHT sent by Bonsai over OSC (UDP), received on a background thread.
"""
import queue
import socket
import struct
import threading
from enum import Enum, auto

import pygame

import config as C
import osc_protocol


class Command(Enum):
    LEFT = auto()       # from keyboard now, from EMG (Bonsai) later
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
    _KEYMAP = (
        (C.KEYS_LEFT, Command.LEFT),
        (C.KEYS_RIGHT, Command.RIGHT),
        (C.KEYS_START, Command.START),
        (C.KEYS_PAUSE, Command.PAUSE),
        (C.KEYS_BACK, Command.BACK),
    )

    def poll(self, pygame_events):
        out = []
        for e in pygame_events:
            if e.type == pygame.KEYDOWN:    # KEYDOWN only -> holding a key = one command
                for keys, cmd in self._KEYMAP:
                    if e.key in keys:
                        out.append(cmd)
                        break
            elif e.type == pygame.QUIT:     # window close button
                out.append(Command.QUIT)
        return out


class OscSource(CommandSource):
    """Receives OSC messages from Bonsai and turns them into LEFT/RIGHT commands.

    Accepted messages (addresses in config.py):
        OSC_ADDRESS_CMD    int 1 -> LEFT, 2 -> RIGHT (0 ignored), or string "LEFT"/"RIGHT"
        OSC_ADDRESS_LEFT   true / non-zero value, or no argument -> LEFT  (false / 0 ignored)
        OSC_ADDRESS_RIGHT  same -> RIGHT
    Menus stay keyboard-only: nothing received over OSC can start, pause or quit the game.
    """

    def __init__(self, host=C.OSC_HOST, port=C.OSC_PORT, trigger=C.OSC_TRIGGER):
        self.host, self.port, self.trigger = host, port, trigger
        self.queue = queue.Queue()
        self.sock = None
        self.thread = None
        self.running = False
        self.status = f"OSC {host}:{port} - not started"
        self.ok = False
        self.n_commands = 0                 # read by the menu (diagnostics)
        self.last_command = None
        self._last_active = {}              # address -> last Command/None, for trigger == "rising"
        self._warned = set()

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
        except OSError as e:
            if self.sock is not None:
                self.sock.close()
                self.sock = None
            self.status = f"OSC ERROR: port {self.port} unavailable ({e.strerror or e})"
            print(f"Warning: {self.status}. Is another game instance running? Keyboard still works.")
            return
        self.sock.settimeout(0.2)           # lets the thread notice stop()
        self.running = True
        self.ok = True
        self.status = f"OSC listening on {self.host}:{self.port}"
        self.thread = threading.Thread(target=self._listen, name="OscSource", daemon=True)
        self.thread.start()

    def _warn_once(self, key, msg):
        if key not in self._warned:
            self._warned.add(key)
            print(f"Warning: {msg}")

    def _listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except ConnectionResetError:    # Windows quirk on UDP sockets; harmless
                continue
            except OSError:                 # socket closed by stop()
                break
            try:
                messages = osc_protocol.parse_packet(data)
            except (ValueError, struct.error, IndexError) as e:
                self._warn_once("malformed", f"ignoring malformed OSC packet ({e})")
                continue
            for address, args in messages:
                self._handle(address, args)

    def _to_command(self, address, args):
        value = args[0] if args else True   # no argument (impulse) = active
        if address == C.OSC_ADDRESS_CMD:
            if isinstance(value, str):
                return {"LEFT": Command.LEFT, "RIGHT": Command.RIGHT}.get(value.strip().upper())
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return {1: Command.LEFT, 2: Command.RIGHT}.get(int(value))
            return None
        if address == C.OSC_ADDRESS_LEFT:
            return Command.LEFT if value else None
        if address == C.OSC_ADDRESS_RIGHT:
            return Command.RIGHT if value else None
        raise KeyError(address)

    def _handle(self, address, args):
        try:
            cmd = self._to_command(address, args)
        except KeyError:
            self._warn_once(address, f"ignoring OSC address {address!r} (expected {C.OSC_ADDRESS_CMD}, "
                                     f"{C.OSC_ADDRESS_LEFT} or {C.OSC_ADDRESS_RIGHT})")
            return
        if self.trigger == "rising":
            previous = self._last_active.get(address)
            self._last_active[address] = cmd
            if cmd == previous:
                return
        if cmd is not None:
            self.n_commands += 1
            self.last_command = cmd
            self.queue.put(cmd)

    def poll(self, pygame_events):
        out = []
        while True:
            try:
                out.append(self.queue.get_nowait())
            except queue.Empty:
                return out

    def stop(self):
        self.running = False
        if self.sock is not None:
            self.sock.close()
        if self.thread is not None:
            self.thread.join(timeout=1)
