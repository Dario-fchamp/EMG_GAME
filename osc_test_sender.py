"""Send LEFT/RIGHT to the game over OSC, exactly like Bonsai would. For testing without Bonsai.

    python osc_test_sender.py              interactive: type l / r (+ ENTER), q to quit
    python osc_test_sender.py --random 20  20 random commands, one every 0.5-1.5 s
"""
import argparse
import random
import socket
import time

import config as C
from osc_protocol import encode_message

CODES = {"l": 1, "r": 2}                    # same convention as Bonsai: 1 = LEFT, 2 = RIGHT


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=C.OSC_HOST)
    parser.add_argument("--port", type=int, default=C.OSC_PORT)
    parser.add_argument("--random", type=int, metavar="N", help="send N random commands")
    args = parser.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (args.host, args.port)

    def send(code):
        sock.sendto(encode_message(C.OSC_ADDRESS_CMD, code), target)
        print(f"sent {C.OSC_ADDRESS_CMD} {code} ({'LEFT' if code == 1 else 'RIGHT'}) to {target[0]}:{target[1]}")

    if args.random:
        for _ in range(args.random):
            send(random.choice((1, 2)))
            time.sleep(random.uniform(0.5, 1.5))
        return
    print("Type l (LEFT) or r (RIGHT) then ENTER; q to quit.")
    while True:
        line = input("> ").strip().lower()
        if line == "q":
            break
        for ch in line:                     # "llr" sends LEFT, LEFT, RIGHT
            if ch in CODES:
                send(CODES[ch])


if __name__ == "__main__":
    main()
