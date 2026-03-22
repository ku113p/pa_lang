"""Tests for PA disassembler."""

from pa.assembler import assemble
from pa.disassembler import disassemble


def test_simple_instruction():
    code = assemble("ad xF\nrt")
    listing = disassemble(code)
    assert "ad" in listing
    assert "xF" in listing
    assert "rt" in listing


def test_expanded_mode():
    code = assemble("ad xF\nrt")
    listing = disassemble(code, expanded=True)
    assert "r1,r3" in listing


def test_sum_bytes_roundtrip():
    source = """\
@L0:
ld mJ
ad xF
ad iB
sb iI
jn qA
rt
"""
    code = assemble(source)
    listing = disassemble(code)
    assert "ld" in listing
    assert "mJ" in listing
    assert "ad" in listing
    assert "rt" in listing


def test_branch_labels_detected():
    source = """\
@L0:
ad iB
jm qA
"""
    code = assemble(source)
    listing = disassemble(code)
    # Should detect a backward branch target and insert a label
    assert "@L0:" in listing
