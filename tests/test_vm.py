"""Tests for PA VM interpreter."""

from pa.assembler import assemble
from pa.vm import VM


def _run_program(source: str, **setup) -> VM:
    """Assemble and run a PA program, returning the VM state."""
    code = assemble(source)
    vm = VM()
    vm.load_program(code)
    for key, val in setup.items():
        if key.startswith("r"):
            vm.r[int(key[1:])] = val
        elif key == "mem":
            addr, data = val
            vm.setup_memory(addr, data)
    vm.run()
    return vm


def test_sum_bytes():
    """Sum bytes [1, 2, 3, 4, 5] = 15."""
    source = """\
@L0:
ld mJ
ad xF
ad iB
sb iI
jn qA
rt
"""
    data = bytes([1, 2, 3, 4, 5])
    vm = _run_program(source, r0=0x1000, r1=0, r2=5, mem=(0x1000, data))
    assert vm.r[1] == 15


def test_sum_bytes_single():
    """Sum single byte [42] = 42."""
    source = """\
@L0:
ld mJ
ad xF
ad iB
sb iI
jn qA
rt
"""
    vm = _run_program(source, r0=0x1000, r1=0, r2=1, mem=(0x1000, bytes([42])))
    assert vm.r[1] == 42


def test_xor_buffer():
    """XOR buffer [0x10, 0x20, 0x30] with key 0xFF."""
    source = """\
@L0:
ld mJ
xr xK
st mJ
ad iB
sb iI
jn qA
rt
"""
    data = bytes([0x10, 0x20, 0x30])
    vm = _run_program(source, r0=0x1000, r1=0xFF, r2=3, mem=(0x1000, data))
    assert vm.mem[0x1000] == 0x10 ^ 0xFF
    assert vm.mem[0x1001] == 0x20 ^ 0xFF
    assert vm.mem[0x1002] == 0x30 ^ 0xFF


def test_find_zero():
    """Find first zero byte in buffer with zero at position 5."""
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
    # 16 bytes: non-zero except position 5
    data = bytearray([0x41] * 16)
    data[5] = 0x00
    vm = _run_program(source, r0=0x1000, mem=(0x1000, bytes(data)))
    assert vm.r[2] == 0x1000 + 5


def test_find_zero_at_start():
    """Zero byte at position 0."""
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
    data = bytearray([0x00] + [0x41] * 15)
    vm = _run_program(source, r0=0x1000, mem=(0x1000, bytes(data)))
    assert vm.r[2] == 0x1000


def test_compare_bufs_equal():
    """Compare two identical 16-byte buffers."""
    source = """\
@L0:
gld gA
gld gD
gcp pE
jn qB
ad iF
ad iM
sb iI
jn qA
mv iA
rt
@F0:
mv iH
rt
"""
    data = bytes(range(16))
    vm = _run_program(source, r0=0x1000, r1=0x2000, r2=1,
                      mem=(0x1000, data))
    vm.setup_memory(0x2000, data)
    # Re-run since setup_memory was after _run_program
    vm2 = VM()
    code = assemble(source)
    vm2.load_program(code)
    vm2.r[0] = 0x1000
    vm2.r[1] = 0x2000
    vm2.r[2] = 1
    vm2.setup_memory(0x1000, data)
    vm2.setup_memory(0x2000, data)
    vm2.run()
    assert vm2.r[0] == 0  # equal


def test_compare_bufs_not_equal():
    """Compare two different 16-byte buffers."""
    source = """\
@L0:
gld gA
gld gD
gcp pE
jn qB
ad iF
ad iM
sb iI
jn qA
mv iA
rt
@F0:
mv iH
rt
"""
    data1 = bytes(range(16))
    data2 = bytes(range(1, 17))
    vm = VM()
    code = assemble(source)
    vm.load_program(code)
    vm.r[0] = 0x1000
    vm.r[1] = 0x2000
    vm.r[2] = 1
    vm.setup_memory(0x1000, data1)
    vm.setup_memory(0x2000, data2)
    vm.run()
    assert vm.r[1] == 1  # not equal


def test_find_delim():
    """Find delimiter 0x2C (comma) in buffer."""
    source = """\
@L0:
gld gA
gcm pF
jn qB
ad iF
sb iI
jn qA
mv iA
rt
@F0:
ffz! r2,p0
ad xG
rt
"""
    data = bytearray([0x41] * 16)
    data[7] = 0x2C  # comma at position 7
    vm = VM()
    code = assemble(source)
    vm.load_program(code)
    vm.r[0] = 0x1000
    vm.r[1] = 0x2C  # delimiter
    vm.r[2] = 1     # 1 block
    vm.setup_memory(0x1000, bytes(data))
    vm.run()
    assert vm.r[2] == 0x1000 + 7


def test_fibonacci():
    """Fibonacci F(10) = 55 — v0.2 uses compact xL."""
    source = """\
@L0:
mv  xK
ad  xD
mv  xL
sb  iI
jn  qA
rt
"""
    vm = _run_program(source, r0=0, r1=1, r2=10)
    assert vm.r[0] == 55


def test_fibonacci_small():
    """Fibonacci F(1) = 1."""
    source = """\
@L0:
mv  xK
ad  xD
mv  xL
sb  iI
jn  qA
rt
"""
    vm = _run_program(source, r0=0, r1=1, r2=1)
    assert vm.r[0] == 1


def test_fibonacci_v01_compat():
    """Fibonacci F(10) = 55 — v0.1 extended syntax still works."""
    source = """\
@L0:
mv  xK
ad  xD
mv! r0,r3
sb  iI
jn  qA
rt
"""
    vm = _run_program(source, r0=0, r1=1, r2=10)
    assert vm.r[0] == 55


def test_min_byte():
    """Minimum of [50, 30, 70, 10, 90] = 10 — v0.2 branchless."""
    source = """\
ld  mE
ad  iB
sb  iI
@L0:
ld  mJ
cm  cE
cs  xF
ad  iB
sb  iI
jn  qA
rt
"""
    data = bytes([50, 30, 70, 10, 90])
    vm = VM()
    code = assemble(source)
    vm.load_program(code)
    vm.setup_memory(0x1000, data)
    vm.r[0] = 0x1000
    vm.r[2] = 5
    vm.run()
    assert vm.r[1] == 10


def test_min_byte_already_first():
    """Minimum is the first byte."""
    source = """\
ld  mE
ad  iB
sb  iI
@L0:
ld  mJ
cm  cE
cs  xF
ad  iB
sb  iI
jn  qA
rt
"""
    data = bytes([5, 30, 70, 80, 90])
    vm = VM()
    code = assemble(source)
    vm.load_program(code)
    vm.setup_memory(0x1000, data)
    vm.r[0] = 0x1000
    vm.r[2] = 5
    vm.run()
    assert vm.r[1] == 5


def test_min_byte_v01_compat():
    """Minimum with v0.1 extended syntax still works."""
    source = """\
ld  mE
ad  iB
sb  iI
@L0:
ld  mJ
cm! r3,r1
jn  qB
mv  xF
@F0:
ad  iB
sb  iI
jn  qA
rt
"""
    data = bytes([50, 30, 70, 10, 90])
    vm = VM()
    code = assemble(source)
    vm.load_program(code)
    vm.setup_memory(0x1000, data)
    vm.r[0] = 0x1000
    vm.r[2] = 5
    vm.run()
    assert vm.r[1] == 10


# ===========================================================================
# External kernel tests (Stage 2 — Phase 1)
# ===========================================================================

import os
from pa.assembler import assemble_file

_PROGRAMS = os.path.join(os.path.dirname(__file__), "..", "programs")


def _run_file(name: str, **setup) -> VM:
    """Assemble a .pa file and run it, returning VM state."""
    code = assemble_file(os.path.join(_PROGRAMS, f"{name}.pa"))
    vm = VM()
    vm.load_program(code)
    for key, val in setup.items():
        if key.startswith("r"):
            vm.r[int(key[1:])] = val
        elif key == "mem":
            addr, data = val
            vm.setup_memory(addr, data)
    return vm


def _run_file_multi_mem(name: str, mems: list, **regs) -> VM:
    """Assemble a .pa file, set up multiple memory regions, run."""
    code = assemble_file(os.path.join(_PROGRAMS, f"{name}.pa"))
    vm = VM()
    vm.load_program(code)
    for key, val in regs.items():
        vm.r[int(key[1:])] = val
    for addr, data in mems:
        vm.setup_memory(addr, data)
    vm.run()
    return vm


# --- K01: ext_memchr ---

def test_ext_memchr_found():
    """memchr: find byte 0x2C at position 7."""
    data = bytearray([0x41] * 16)
    data[7] = 0x2C
    vm = _run_file("ext_memchr", r0=0x1000, r1=0x2C, r2=1, mem=(0x1000, bytes(data)))
    vm.run()
    assert vm.r[2] == 0x1000 + 7


def test_ext_memchr_not_found():
    """memchr: byte not in buffer."""
    data = bytes([0x41] * 16)
    vm = _run_file("ext_memchr", r0=0x1000, r1=0x2C, r2=1, mem=(0x1000, data))
    vm.run()
    assert vm.r[0] == 0


# --- K02: ext_memcmp ---

def test_ext_memcmp_equal():
    """memcmp: two identical 16-byte buffers."""
    data = bytes(range(16))
    vm = _run_file_multi_mem("ext_memcmp",
                             [(0x1000, data), (0x2000, data)],
                             r0=0x1000, r1=0x2000, r2=1)
    assert vm.r[0] == 0


def test_ext_memcmp_not_equal():
    """memcmp: two different 16-byte buffers."""
    data1 = bytes(range(16))
    data2 = bytes(range(1, 17))
    vm = _run_file_multi_mem("ext_memcmp",
                             [(0x1000, data1), (0x2000, data2)],
                             r0=0x1000, r1=0x2000, r2=1)
    assert vm.r[0] == 1


# --- K03: ext_strlen ---

def test_ext_strlen():
    """strlen: null at position 5."""
    data = bytearray([0x41] * 16)
    data[5] = 0x00
    vm = _run_file("ext_strlen", r0=0x1000, mem=(0x1000, bytes(data)))
    vm.run()
    assert vm.r[2] == 0x1000 + 5


def test_ext_strlen_at_start():
    """strlen: null at position 0."""
    data = bytearray([0x00] + [0x41] * 15)
    vm = _run_file("ext_strlen", r0=0x1000, mem=(0x1000, bytes(data)))
    vm.run()
    assert vm.r[2] == 0x1000


# --- K04: ext_find_mismatch ---

def test_ext_find_mismatch_found():
    """find_mismatch: buffers differ at position 3."""
    data1 = bytes([0x41] * 16)
    data2 = bytearray([0x41] * 16)
    data2[3] = 0x42
    vm = _run_file_multi_mem("ext_find_mismatch",
                             [(0x1000, data1), (0x2000, bytes(data2))],
                             r0=0x1000, r1=0x2000, r2=1)
    assert vm.r[2] == 0x1000 + 3


def test_ext_find_mismatch_equal():
    """find_mismatch: identical buffers."""
    data = bytes(range(16))
    vm = _run_file_multi_mem("ext_find_mismatch",
                             [(0x1000, data), (0x2000, data)],
                             r0=0x1000, r1=0x2000, r2=1)
    assert vm.r[0] == 0


# --- K05: ext_prefix_eq ---

def test_ext_prefix_eq_equal():
    """prefix_eq: matching 16-byte prefixes."""
    data = bytes(range(16))
    vm = _run_file_multi_mem("ext_prefix_eq",
                             [(0x1000, data), (0x2000, data)],
                             r0=0x1000, r1=0x2000)
    assert vm.r[0] == 0


def test_ext_prefix_eq_not_equal():
    """prefix_eq: differing 16-byte prefixes."""
    data1 = bytes(range(16))
    data2 = bytes(range(1, 17))
    vm = _run_file_multi_mem("ext_prefix_eq",
                             [(0x1000, data1), (0x2000, data2)],
                             r0=0x1000, r1=0x2000)
    assert vm.r[0] == 1


# --- K06: ext_strchr ---

def test_ext_strchr_found():
    """strchr: find byte 0x2C in null-terminated string."""
    data = bytearray([0x41, 0x42, 0x43, 0x2C, 0x44, 0x00])
    vm = _run_file("ext_strchr", r0=0x1000, r1=0x2C, mem=(0x1000, bytes(data)))
    vm.run()
    assert vm.r[2] == 0x1000 + 3


def test_ext_strchr_not_found():
    """strchr: byte not in string (hit null)."""
    data = bytearray([0x41, 0x42, 0x43, 0x00])
    vm = _run_file("ext_strchr", r0=0x1000, r1=0x2C, mem=(0x1000, bytes(data)))
    vm.run()
    assert vm.r[0] == 0


# --- K07: ext_bytecount ---

def test_ext_bytecount():
    """bytecount: count 0x41 in buffer."""
    data = bytes([0x41, 0x42, 0x41, 0x43, 0x41])
    vm = _run_file("ext_bytecount", r0=0x1000, r1=0x41, r2=5,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[1] == 3


def test_ext_bytecount_none():
    """bytecount: no matches."""
    data = bytes([0x42, 0x43, 0x44])
    vm = _run_file("ext_bytecount", r0=0x1000, r1=0x41, r2=3,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[1] == 0


# --- K08: ext_find_byte_lt ---

def test_ext_find_byte_lt_found():
    """find_byte_lt: find first byte < 0x20 (control char)."""
    data = bytes([0x41, 0x42, 0x43, 0x0A, 0x44])
    vm = _run_file("ext_find_byte_lt", r0=0x1000, r1=0x20, r2=5,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[2] == 0x1000 + 3


def test_ext_find_byte_lt_not_found():
    """find_byte_lt: all bytes >= threshold."""
    data = bytes([0x41, 0x42, 0x43])
    vm = _run_file("ext_find_byte_lt", r0=0x1000, r1=0x20, r2=3,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[0] == 0


# --- K09: ext_find_byte_gt ---

def test_ext_find_byte_gt_found():
    """find_byte_gt: find first byte > 0x7F (non-ASCII)."""
    data = bytes([0x41, 0x42, 0x80, 0x43])
    vm = _run_file("ext_find_byte_gt", r0=0x1000, r1=0x7F, r2=4,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[2] == 0x1000 + 2


def test_ext_find_byte_gt_not_found():
    """find_byte_gt: all bytes <= threshold."""
    data = bytes([0x41, 0x42, 0x43])
    vm = _run_file("ext_find_byte_gt", r0=0x1000, r1=0x7F, r2=3,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[0] == 0


# --- K10: ext_memchr2 ---

def test_ext_memchr2_first_byte():
    """memchr2: find first of two bytes — byte1 found."""
    data = bytes([0x41, 0x42, 0x2C, 0x43])
    vm = _run_file("ext_memchr2", r0=0x1000, r1=0x2C, r2=4, r3=0x3A,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[2] == 0x1000 + 2


def test_ext_memchr2_second_byte():
    """memchr2: find first of two bytes — byte2 found first."""
    data = bytes([0x41, 0x3A, 0x42, 0x2C])
    vm = _run_file("ext_memchr2", r0=0x1000, r1=0x2C, r2=4, r3=0x3A,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[2] == 0x1000 + 1


# --- K11: ext_find_nonascii ---

def test_ext_find_nonascii_found():
    """find_nonascii: byte 0x80 at position 3."""
    data = bytes([0x41, 0x42, 0x43, 0x80, 0x44])
    vm = _run_file("ext_find_nonascii", r0=0x1000, r1=127, r2=5,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[2] == 0x1000 + 3


def test_ext_find_nonascii_all_ascii():
    """find_nonascii: all bytes are ASCII."""
    data = bytes([0x41, 0x42, 0x43])
    vm = _run_file("ext_find_nonascii", r0=0x1000, r1=127, r2=3,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[0] == 0


# --- K12: ext_memrchr ---

def test_ext_memrchr_found():
    """memrchr: find last 0x2C scanning backward."""
    data = bytes([0x41, 0x2C, 0x42, 0x2C, 0x43])
    # r0 = one past end, r1 = byte, r2 = length
    vm = _run_file("ext_memrchr", r0=0x1000 + 5, r1=0x2C, r2=5,
                   mem=(0x1000, data))
    vm.run()
    # Last 0x2C is at position 3
    assert vm.r[2] == 0x1000 + 3


def test_ext_memrchr_not_found():
    """memrchr: byte not in buffer."""
    data = bytes([0x41, 0x42, 0x43])
    vm = _run_file("ext_memrchr", r0=0x1000 + 3, r1=0x2C, r2=3,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[0] == 0


# --- K13: ext_memset ---

def test_ext_memset():
    """memset: fill 5 bytes with 0xAA."""
    vm = _run_file("ext_memset", r0=0x1000, r1=0xAA, r2=5,
                   mem=(0x1000, bytes(5)))
    vm.run()
    for i in range(5):
        assert vm.mem[0x1000 + i] == 0xAA


def test_ext_memset_single():
    """memset: fill 1 byte."""
    vm = _run_file("ext_memset", r0=0x1000, r1=0x42, r2=1,
                   mem=(0x1000, bytes(1)))
    vm.run()
    assert vm.mem[0x1000] == 0x42


# --- K14: ext_strspn ---

def test_ext_strspn_match():
    """strspn: count leading 0x41 bytes."""
    data = bytes([0x41, 0x41, 0x41, 0x42, 0x41, 0x00])
    vm = _run_file("ext_strspn", r0=0x1000, r1=0x41,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[1] == 3


def test_ext_strspn_no_match():
    """strspn: first byte not in accept set."""
    data = bytes([0x42, 0x41, 0x41, 0x00])
    vm = _run_file("ext_strspn", r0=0x1000, r1=0x41,
                   mem=(0x1000, data))
    vm.run()
    assert vm.r[1] == 0


# ===========================================================================
# v0.2 feature tests
# ===========================================================================

def test_v02_compact_ffz():
    """Compact ffz fA produces same result as extended ffz!."""
    # ffz fA = r2 = find_first_set(p0)
    source_compact = """\
@L0:
gld gA
gcm pA
jn qB
ad iF
jm qA
@F0:
ffz fA
ad xG
rt
"""
    source_extended = """\
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
    data = bytearray([0x41] * 16)
    data[7] = 0x00
    vm1 = _run_program(source_compact, r0=0x1000, mem=(0x1000, bytes(data)))
    vm2 = _run_program(source_extended, r0=0x1000, mem=(0x1000, bytes(data)))
    assert vm1.r[2] == vm2.r[2] == 0x1000 + 7
    # Compact is 1 byte shorter
    assert len(assemble(source_compact)) == len(assemble(source_extended)) - 1


def test_v02_compact_cm():
    """Compact cm cells set condition correctly."""
    # cm cE: condition = (r3 < r1)
    source = """\
cm cE
jn qB
mv iB
rt
@F0:
mv iA
rt
"""
    # r3=5, r1=10: 5 < 10 = true → jn jumps → mv iA → r0=0
    vm = _run_program(source, r1=10, r3=5)
    assert vm.r[0] == 0  # condition was true, jumped to @F0

    # r3=10, r1=5: 10 < 5 = false → falls through → mv iB → r0=1
    vm = _run_program(source, r1=5, r3=10)
    assert vm.r[0] == 1  # condition was false, fell through


def test_v02_conditional_select():
    """cs (conditional select) moves only when condition is true."""
    # cs xA: if condition, r0 := r1
    source_true = """\
cm cC
cs xA
rt
"""
    # r0=10, r1=5: cm cC = (r0 > r1) = true → cs xA moves r1→r0
    vm = _run_program(source_true, r0=10, r1=5)
    assert vm.r[0] == 5  # moved

    # r0=3, r1=5: cm cC = (r0 > r1) = false → cs xA is no-op
    vm = _run_program(source_true, r0=3, r1=5)
    assert vm.r[0] == 3  # not moved


def test_v02_cs_preserves_condition():
    """cs does NOT update condition flag."""
    source = """\
cm cC
cs xA
jn qB
mv iB
rt
@F0:
mv iA
rt
"""
    # r0=10, r1=5: cm cC = true (10>5). cs xA moves (r0=5). jn checks ORIGINAL condition (true) → jumps to @F0
    vm = _run_program(source, r0=10, r1=5)
    assert vm.r[0] == 0  # jumped to @F0, confirming condition preserved

    # r0=3, r1=5: cm cC = false (3<5). cs xA no-op (r0 stays 3). jn false → falls through → mv iB → r0=1
    vm = _run_program(source, r0=3, r1=5)
    assert vm.r[0] == 1  # fell through


def test_v02_register_pair_xL():
    """xL cell: r0 := r3."""
    source = """\
mv xL
rt
"""
    vm = _run_program(source, r3=42)
    assert vm.r[0] == 42


def test_v02_bytecode_sizes():
    """v0.2 kernels are smaller than v0.1."""
    from pa.assembler import assemble_file
    # find_zero: was 16B (with ffz!), now 15B (with ffz fA)
    assert len(assemble_file(os.path.join(_PROGRAMS, "find_zero.pa"))) == 15
    # fibonacci: was 12B (with mv!), now 11B (with mv xL)
    assert len(assemble_file(os.path.join(_PROGRAMS, "fibonacci.pa"))) == 11
    # min_byte: was 22B (cm! + jn + mv + @F0), now 19B (cm cE + cs xF, branchless)
    assert len(assemble_file(os.path.join(_PROGRAMS, "min_byte.pa"))) == 19
