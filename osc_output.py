"""OSC events sent from the game to Bonsai (e.g. a star was caught -> Bonsai plays a sound on a Harp board)."""
import socket

import osc_protocol


class OscSender:
    """Fire-and-forget OSC over UDP: never blocks the game, never crashes it if Bonsai isn't listening."""

    def __init__(self, host, port):
        self.target = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.n_sent = 0
        self._warned = False

    def send(self, address, *args):
        try:
            self.sock.sendto(osc_protocol.encode_message(address, *args), self.target)
            self.n_sent += 1
        except OSError as e:
            if not self._warned:
                self._warned = True
                print(f"Warning: could not send OSC {address} to {self.target[0]}:{self.target[1]} ({e}).")

    def close(self):
        self.sock.close()
