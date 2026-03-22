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
    """Fibonacci F(10) = 55."""
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


def test_fibonacci_small():
    """Fibonacci F(1) = 1."""
    source = """\
@L0:
mv  xK
ad  xD
mv! r0,r3
sb  iI
jn  qA
rt
"""
    vm = _run_program(source, r0=0, r1=1, r2=1)
    assert vm.r[0] == 1


def test_min_byte():
    """Minimum of [50, 30, 70, 10, 90] = 10."""
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


def test_min_byte_already_first():
    """Minimum is the first byte."""
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
    data = bytes([5, 30, 70, 80, 90])
    vm = VM()
    code = assemble(source)
    vm.load_program(code)
    vm.setup_memory(0x1000, data)
    vm.r[0] = 0x1000
    vm.r[2] = 5
    vm.run()
    assert vm.r[1] == 5
