"""Tests for PA bytecode format."""

import tempfile
import os
import pytest
from pa.bytecode import write_bytecode, read_bytecode, pack_bytecode, BytecodeError, MAGIC, HEADER_SIZE


def test_pack_roundtrip():
    code = bytes([0x13, 0x02, 0x1E])  # ad xF, rt
    packed = pack_bytecode(code)
    assert packed[:4] == MAGIC
    assert len(packed) == HEADER_SIZE + len(code)


def test_file_roundtrip():
    code = bytes([0x13, 0x02, 0x11, 0x23, 0x1E])
    with tempfile.NamedTemporaryFile(suffix=".pac", delete=False) as f:
        path = f.name
    try:
        write_bytecode(code, path)
        result = read_bytecode(path)
        assert result == code
    finally:
        os.unlink(path)


def test_bad_magic():
    with tempfile.NamedTemporaryFile(suffix=".pac", delete=False) as f:
        f.write(b"XXXX\x00\x00\x03\x00ABC")
        path = f.name
    try:
        with pytest.raises(BytecodeError):
            read_bytecode(path)
    finally:
        os.unlink(path)


def test_truncated_file():
    with tempfile.NamedTemporaryFile(suffix=".pac", delete=False) as f:
        f.write(b"PA")  # too short for header
        path = f.name
    try:
        with pytest.raises(BytecodeError):
            read_bytecode(path)
    finally:
        os.unlink(path)
