"""Tests for PA assembler."""

import pytest
from pa.assembler import assemble, AssemblyError
from pa.isa import OPCODES, CELLS, ESCAPES


def test_simple_rt():
    code = assemble("rt")
    assert code == bytes([OPCODES["rt"][0]])


def test_simple_alu():
    code = assemble("ad xF")
    assert code == bytes([OPCODES["ad"][0], CELLS["xF"][0]])


def test_immediate_cell():
    code = assemble("ad iB")
    assert code == bytes([OPCODES["ad"][0], CELLS["iB"][0]])


def test_memory_cell():
    code = assemble("ld mJ")
    assert code == bytes([OPCODES["ld"][0], CELLS["mJ"][0]])


def test_group_cell():
    code = assemble("gld gA")
    assert code == bytes([OPCODES["gld"][0], CELLS["gA"][0]])


def test_predicate_cell():
    code = assemble("gcm pA")
    assert code == bytes([OPCODES["gcm"][0], CELLS["pA"][0]])


def test_comments_ignored():
    code = assemble("; this is a comment\nad xF ; inline comment")
    assert code == bytes([OPCODES["ad"][0], CELLS["xF"][0]])


def test_blank_lines_ignored():
    code = assemble("\n\nad xF\n\nrt\n")
    assert len(code) == 3  # ad(1) + cell(1) + rt(1)


def test_ffz_extended():
    code = assemble("ffz! r2,p0")
    assert code == bytes([ESCAPES["ex3"], OPCODES["ffz"][0], 0x20])


def test_unknown_mnemonic():
    with pytest.raises(AssemblyError):
        assemble("xyz xA")


def test_unknown_cell():
    with pytest.raises(AssemblyError):
        assemble("ad zZ")


def test_missing_cell():
    with pytest.raises(AssemblyError):
        assemble("ad")


def test_sum_bytes_assembles():
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
    # 5 two-byte instructions + 1 one-byte rt = 11 bytes
    assert len(code) == 11


def test_find_zero_assembles():
    source = """\
@L0:
gld gA
gcm pA
jn qB
ad iF
jm qA
@F0:
ffz! r2,p0
ad xG
rt
"""
    code = assemble(source)
    # 6 two-byte + 1 three-byte (ffz) + 1 one-byte (rt) = 16 bytes
    assert len(code) == 16


def test_backward_branch_resolves():
    source = """\
@L0:
ad iB
jm qA
"""
    code = assemble(source)
    # ad iB = 2 bytes at offset 0
    # jm at offset 2, cell byte should be relative: target=0, from end of jm=4, rel=-4
    assert code[3] == (-4) & 0xFF  # 0xFC


def test_forward_branch_resolves():
    source = """\
jn qB
ad iB
@F0:
rt
"""
    code = assemble(source)
    # jn at offset 0, end at offset 2
    # @F0 at offset 4 (after ad iB which is 2 bytes)
    # rel = 4 - 2 = 2
    assert code[1] == 2
