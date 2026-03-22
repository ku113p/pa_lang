"""PA bytecode binary format — read/write.

Format:
  Header (8 bytes):
    magic:   4 bytes  b"PA\\x00\\x01"
    flags:   1 byte   0x00
    unused:  1 byte   0x00
    codelen: 2 bytes  little-endian uint16

  Code section:
    codelen bytes of raw instruction data
"""

import struct

MAGIC = b"PA\x00\x01"
HEADER_FORMAT = "<4sBBH"  # magic(4s) + flags(B) + unused(B) + codelen(H)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class BytecodeError(Exception):
    pass


def write_bytecode(code: bytes, path: str) -> None:
    """Write bytecode to a .pac file."""
    if len(code) > 0xFFFF:
        raise BytecodeError(f"code too large: {len(code)} bytes (max 65535)")
    header = struct.pack(HEADER_FORMAT, MAGIC, 0, 0, len(code))
    with open(path, "wb") as f:
        f.write(header)
        f.write(code)


def read_bytecode(path: str) -> bytes:
    """Read bytecode from a .pac file."""
    with open(path, "rb") as f:
        header_data = f.read(HEADER_SIZE)
        if len(header_data) < HEADER_SIZE:
            raise BytecodeError("file too short for header")
        magic, flags, _, codelen = struct.unpack(HEADER_FORMAT, header_data)
        if magic != MAGIC:
            raise BytecodeError(f"bad magic: {magic!r}")
        code = f.read(codelen)
        if len(code) < codelen:
            raise BytecodeError(f"truncated code: expected {codelen}, got {len(code)}")
        return code


def pack_bytecode(code: bytes) -> bytes:
    """Return header + code as bytes (no file I/O)."""
    if len(code) > 0xFFFF:
        raise BytecodeError(f"code too large: {len(code)} bytes (max 65535)")
    header = struct.pack(HEADER_FORMAT, MAGIC, 0, 0, len(code))
    return header + code
