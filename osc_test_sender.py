"""Send LEFT/RIGHT to the game over OSC, exactly like the Bonsai workflow would. For testing without Bonsai.

Sends OSC_ADDRESS_PAIR (/mcoords) with two ints (left, right), type tag "ii", like Bonsai's
Zip -> SendMessage: a "contraction" is (1, 0) then (0, 0) for LEFT, (0, 1) then (0, 0) for RIGHT.

    python osc_test_sender.py              interactive: type l / r (+ ENTER), q to quit
    python osc_test_sender.py --random 20  20 random commands, one every 0.5-1.5 s
"""
import argparse
import random
import socket
import time

import config as C
from osc_protocol import encode_message

PRESS = {"l": (1, 0), "r": (0, 1)}
RELEASE = (0, 0)
HOLD_TIME = 0.15                            # s between "press" and "release", like a short contraction


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=C.OSC_HOST)
    parser.add_argument("--port", type=int, default=C.OSC_PORT)
    parser.add_argument("--random", type=int, metavar="N", help="send N random commands")
    args = parser.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (args.host, args.port)

    def contraction(key):
        sock.sendto(encode_message(C.OSC_ADDRESS_PAIR, *PRESS[key]), target)
        time.sleep(HOLD_TIME)
        sock.sendto(encode_message(C.OSC_ADDRESS_PAIR, *RELEASE), target)
        print(f"sent {C.OSC_ADDRESS_PAIR} {PRESS[key]} -> {RELEASE}  "
              f"({'LEFT' if key == 'l' else 'RIGHT'}) to {target[0]}:{target[1]}")

    if args.random:
        for _ in range(args.random):
            contraction(random.choice("lr"))
            time.sleep(random.uniform(0.5, 1.5))
        return
    print("Type l (LEFT) or r (RIGHT) then ENTER; q to quit. 'llr' = LEFT, LEFT, RIGHT.")
    while True:
        line = input("> ").strip().lower()
        if line == "q":
            break
        for ch in line:
            if ch in PRESS:
                contraction(ch)


if __name__ == "__main__":
    main()
