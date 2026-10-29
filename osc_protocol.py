"""Minimal OSC 1.0 encoder/decoder (no external dependency), enough for Bonsai.Osc messages.

OSC packet = message or bundle. Message = address string, type-tag string (",iis"...), arguments.
Strings are null-terminated and padded to 4 bytes; numbers are big-endian.
"""
import struct

_FIXED = {"i": (">i", 4), "f": (">f", 4), "h": (">q", 8), "d": (">d", 8),
          "c": (">i", 4), "r": (">I", 4), "t": (">Q", 8)}
_CONST = {"T": True, "F": False, "N": None, "I": None}


def _read_string(data, i):
    end = data.index(b"\0", i)
    return data[i:end].decode("utf-8", errors="replace"), (end + 4) & ~3   # skip null + padding


def _read_blob(data, i):
    (n,) = struct.unpack_from(">i", data, i)
    i += 4
    return data[i:i + n], i + ((n + 3) & ~3)


def parse_message(data):
    """Return (address, [args]). Raises ValueError / struct.error on malformed data."""
    address, i = _read_string(data, 0)
    if i >= len(data):                      # no type-tag string: no arguments
        return address, []
    tags, i = _read_string(data, i)
    if not tags.startswith(","):
        raise ValueError(f"missing type-tag string in message to {address}")
    args = []
    for tag in tags[1:]:
        if tag in _FIXED:
            fmt, size = _FIXED[tag]
            (value,) = struct.unpack_from(fmt, data, i)
            i += size
        elif tag in "sS":
            value, i = _read_string(data, i)
        elif tag == "b":
            value, i = _read_blob(data, i)
        elif tag in _CONST:
            value = _CONST[tag]
        elif tag == "m":
            value, i = data[i:i + 4], i + 4
        elif tag in "[]":                   # arrays are flattened
            continue
        else:
            raise ValueError(f"unsupported OSC type tag {tag!r}")
        args.append(value)
    return address, args


def parse_packet(data):
    """Return a list of (address, args) from a message or a (nested) bundle."""
    if data.startswith(b"#bundle\0"):
        out, i = [], 16                     # skip "#bundle\0" + 8-byte time tag
        while i + 4 <= len(data):
            (n,) = struct.unpack_from(">i", data, i)
            i += 4
            out += parse_packet(data[i:i + n])
            i += n
        return out
    return [parse_message(data)]


def _padded(b):
    return b + b"\0" * (4 - len(b) % 4)     # always at least one null


def encode_message(address, *args):
    """Build an OSC message (used by osc_test_sender.py). Supports bool, int, float, str."""
    tags, payload = ",", b""
    for a in args:
        if isinstance(a, bool):
            tags += "T" if a else "F"
        elif isinstance(a, int):
            tags += "i"
            payload += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"
            payload += struct.pack(">f", a)
        elif isinstance(a, str):
            tags += "s"
            payload += _padded(a.encode("utf-8"))
        else:
            raise TypeError(f"unsupported OSC argument type: {type(a).__name__}")
    return _padded(address.encode("utf-8")) + _padded(tags.encode("ascii")) + payload
