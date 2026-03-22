#!/usr/bin/env python3
"""PA benchmark harness — source and bytecode size comparisons."""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pa.assembler import assemble_file
from pa.isa import OPCODE_BY_BYTE, OPCODES, ESCAPE_BYTES
from pa.vm import VM

PROGRAMS_DIR = os.path.join(os.path.dirname(__file__), "..", "programs")
REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "reference")
WASM_DIR = os.path.join(os.path.dirname(__file__), "wasm")

KERNELS = [
    "sum_bytes",
    "find_zero",
    "xor_buffer",
    "compare_bufs",
    "find_delim",
    "fibonacci",
    "min_byte",
]

NEGATIVE_CASES = {"fibonacci", "min_byte"}

EXTERNAL_KERNELS = [
    "ext_memchr",
    "ext_memcmp",
    "ext_strchr",
    "ext_strlen",
    "ext_find_nonascii",
    "ext_bytecount",
    "ext_find_mismatch",
    "ext_prefix_eq",
    "ext_find_byte_lt",
    "ext_find_byte_gt",
    "ext_memrchr",
    "ext_memchr2",
    "ext_strspn",
    "ext_memset",
]

EXTERNAL_CLASSIFICATION = {
    "ext_memchr": "A",
    "ext_memcmp": "A",
    "ext_strchr": "B",
    "ext_strlen": "A",
    "ext_find_nonascii": "C",
    "ext_bytecount": "B",
    "ext_find_mismatch": "A",
    "ext_prefix_eq": "A",
    "ext_find_byte_lt": "B",
    "ext_find_byte_gt": "B",
    "ext_memrchr": "C",
    "ext_memchr2": "B",
    "ext_strspn": "C",
    "ext_memset": "B",
}

# x86 machine code sizes — fallback estimates if nasm unavailable
X86_CODE_SIZES_EST = {
    "sum_bytes": 14,
    "find_zero": 28,
    "xor_buffer": 15,
    "compare_bufs": 38,
    "find_delim": 42,
    "fibonacci": 12,
    "min_byte": 24,
    "ext_memchr": 40,
    "ext_memcmp": 25,
    "ext_strchr": 20,
    "ext_strlen": 28,
    "ext_find_nonascii": 26,
    "ext_bytecount": 18,
    "ext_find_mismatch": 38,
    "ext_prefix_eq": 24,
    "ext_find_byte_lt": 20,
    "ext_find_byte_gt": 20,
    "ext_memrchr": 38,
    "ext_memchr2": 22,
    "ext_strspn": 18,
    "ext_memset": 10,
}


def measure_x86_size(asm_path):
    """Assemble x86 with nasm flat binary, return actual size. Falls back to estimate."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            tmp_path = tmp.name
        result = subprocess.run(
            ["nasm", "-f", "bin", "-o", tmp_path, asm_path],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            size = os.path.getsize(tmp_path)
            os.unlink(tmp_path)
            return size, True  # (size, assembled)
        os.unlink(tmp_path)
    except FileNotFoundError:
        pass  # nasm not installed
    name = os.path.splitext(os.path.basename(asm_path))[0]
    return X86_CODE_SIZES_EST.get(name, 0), False


def wasm_code_body_size(path):
    """Extract instruction byte count from .wasm file (code section, excluding locals)."""
    data = open(path, "rb").read()
    pos = 8  # skip magic + version
    while pos < len(data):
        section_id = data[pos]; pos += 1
        size = 0; shift = 0
        while True:
            b = data[pos]; pos += 1
            size |= (b & 0x7F) << shift; shift += 7
            if not (b & 0x80): break
        if section_id == 10:  # Code section
            # func count
            fc = 0; shift = 0
            while True:
                b = data[pos]; pos += 1
                fc |= (b & 0x7F) << shift; shift += 7
                if not (b & 0x80): break
            # body size
            body_size = 0; shift = 0
            while True:
                b = data[pos]; pos += 1
                body_size |= (b & 0x7F) << shift; shift += 7
                if not (b & 0x80): break
            # locals count
            lc = 0; shift = 0
            while True:
                b = data[pos]; pos += 1
                lc |= (b & 0x7F) << shift; shift += 7
                if not (b & 0x80): break
            locals_bytes = 0
            for _ in range(lc):
                while data[pos] & 0x80: pos += 1; locals_bytes += 1
                pos += 1; locals_bytes += 1
                pos += 1; locals_bytes += 1
            instr_bytes = body_size - 1 - locals_bytes
            return instr_bytes
        else:
            pos += size
    return 0


def compile_wat_files():
    """Compile all .wat files to .wasm."""
    for name in KERNELS:
        wat = os.path.join(WASM_DIR, f"{name}.wat")
        wasm = os.path.join(WASM_DIR, f"{name}.wasm")
        if os.path.exists(wat):
            subprocess.run(["wat2wasm", wat, "-o", wasm], capture_output=True)


def count_instruction_types(bytecode):
    """Count compact, extended, and no-operand instructions."""
    compact = extended = no_operand = 0
    pc = 0
    while pc < len(bytecode):
        b = bytecode[pc]
        if b in ESCAPE_BYTES:
            extended += 1; pc += 3
        elif b in OPCODE_BY_BYTE:
            if OPCODES[OPCODE_BY_BYTE[b]][2]:
                compact += 1; pc += 2
            else:
                no_operand += 1; pc += 1
        else:
            pc += 1
    return compact, extended, no_operand


def measure_kernel(name):
    """Measure a single kernel's sizes. Returns dict of metrics."""
    pa_path = os.path.join(PROGRAMS_DIR, f"{name}.pa")
    asm_path = os.path.join(REFERENCE_DIR, f"{name}.asm")

    # PA source
    with open(pa_path) as f:
        pa_source = f.read()
    pa_code_lines = [
        l.split(";")[0].strip()
        for l in pa_source.splitlines()
        if l.split(";")[0].strip() and not l.split(";")[0].strip().startswith(";")
    ]
    pa_code_bytes = len("\n".join(pa_code_lines).encode("utf-8"))

    # PA bytecode
    bytecode = assemble_file(pa_path)
    pa_bytecode_size = len(bytecode)
    compact, extended, no_op = count_instruction_types(bytecode)
    total_instr = compact + extended + no_op
    coverage = compact / total_instr * 100 if total_instr else 0

    # x86 asm source
    with open(asm_path) as f:
        asm_source = f.read()
    asm_code_lines = [
        l.split(";")[0].strip()
        for l in asm_source.splitlines()
        if l.split(";")[0].strip() and not l.split(";")[0].strip().startswith(";")
    ]
    asm_code_bytes = len("\n".join(asm_code_lines).encode("utf-8"))
    x86_machine, x86_assembled = measure_x86_size(asm_path)

    # x86 instruction count
    asm_instr_count = sum(1 for l in asm_code_lines if not l.endswith(":") and l)

    # PA instruction count
    pa_instr_count = sum(1 for l in pa_code_lines if not l.startswith("@"))

    # Wasm (optional)
    wasm_path = os.path.join(WASM_DIR, f"{name}.wasm")
    wat_path = os.path.join(WASM_DIR, f"{name}.wat")
    wasm_instr = 0
    wasm_total = 0
    wat_code_bytes = 0
    if os.path.exists(wasm_path):
        wasm_instr = wasm_code_body_size(wasm_path)
        wasm_total = os.path.getsize(wasm_path)
    if os.path.exists(wat_path):
        with open(wat_path) as f:
            wat_src = f.read()
        wat_lines = [l.strip() for l in wat_src.splitlines() if l.strip() and not l.strip().startswith(";;")]
        wat_code_bytes = len("\n".join(wat_lines).encode("utf-8"))

    return {
        "name": name,
        "pa_code": pa_code_bytes,
        "pa_bytecode": pa_bytecode_size,
        "pa_instr": pa_instr_count,
        "asm_code": asm_code_bytes,
        "asm_instr": asm_instr_count,
        "x86_machine": x86_machine,
        "x86_assembled": x86_assembled,
        "wasm_instr": wasm_instr,
        "wasm_total": wasm_total,
        "wat_code": wat_code_bytes,
        "compact": compact,
        "extended": extended,
        "coverage": coverage,
    }


def measure_sizes():
    compile_wat_files()
    return [measure_kernel(name) for name in KERNELS]


def measure_external():
    return [measure_kernel(name) for name in EXTERNAL_KERNELS]


def print_results(results):
    print("\n" + "=" * 95)
    print("PA BENCHMARK RESULTS — Source & Bytecode Size Comparison")
    print("=" * 95)

    x86_note = "assembled" if results[0]["x86_assembled"] else "estimated"

    # Table header
    print(f"\n{'Kernel':<14} {'PA src':>6} {'x86':>5} {'Ratio':>5} | "
          f"{'PA bc':>5} {'x86':>5} {'Wasm':>5} {'PA/x86':>6} {'PA/Wasm':>7} | "
          f"{'Ext':>4} {'Cov':>5}")
    print(f"{'':14} {'':>6} {'src':>5} {'':>5} | "
          f"{'':>5} {f'({x86_note[:3]})':>5} {'instr':>5} {'':>6} {'':>7} | "
          f"{'':>4} {'':>5}")
    print("-" * 95)

    for r in results:
        src_ratio = r["pa_code"] / r["asm_code"] * 100 if r["asm_code"] else 0
        bc_x86 = r["pa_bytecode"] / r["x86_machine"] * 100 if r["x86_machine"] else 0
        bc_wasm = r["pa_bytecode"] / r["wasm_instr"] * 100 if r["wasm_instr"] else 0
        ext_str = f"{r['extended']}" if r["extended"] else "-"
        print(f"{r['name']:<14} {r['pa_code']:>4}B {r['asm_code']:>4}B {src_ratio:>4.0f}% | "
              f"{r['pa_bytecode']:>3}B {r['x86_machine']:>4}B {r['wasm_instr']:>4}B {bc_x86:>5.0f}% {bc_wasm:>6.0f}% | "
              f"{ext_str:>4} {r['coverage']:>4.0f}%")

    # Totals and averages
    total_pa_src = sum(r["pa_code"] for r in results)
    total_x86_src = sum(r["asm_code"] for r in results)
    total_pa_bc = sum(r["pa_bytecode"] for r in results)
    total_x86_mc = sum(r["x86_machine"] for r in results)
    total_wasm = sum(r["wasm_instr"] for r in results)
    total_instr = sum(r["pa_instr"] for r in results)

    w_src = total_pa_src / total_x86_src * 100 if total_x86_src else 0
    w_x86 = total_pa_bc / total_x86_mc * 100 if total_x86_mc else 0
    w_wasm = total_pa_bc / total_wasm * 100 if total_wasm else 0
    avg_bpi = total_pa_bc / total_instr if total_instr else 0

    print("-" * 95)
    print(f"{'Weighted avg':<14} {'':>4}  {'':>4}  {w_src:>4.0f}% | "
          f"{'':>3}  {'':>4}  {'':>4}  {w_x86:>5.0f}% {w_wasm:>6.0f}% |")

    print(f"\nPA bytes/instruction (avg): {avg_bpi:.2f}")
    print(f"x86 machine code: {x86_note}")
    print()

    # Assessment
    print("--- Assessment vs Success Criteria ---")
    print(f"  Source ratio target: ≤60%  →  actual: {w_src:.0f}%  "
          f"{'PASS' if w_src <= 60 else 'REVIEW' if w_src <= 70 else 'FAIL'}")
    print(f"  Bytes/instruction target: ≤2.5  →  actual: {avg_bpi:.2f}  "
          f"{'PASS' if avg_bpi <= 2.5 else 'FAIL'}")
    print(f"  PA vs Wasm bytecode: {w_wasm:.0f}% (PA is {100-w_wasm:.0f}% smaller)")
    print()


def verify_correctness():
    """Run each kernel with test data to verify it produces correct results."""
    print("--- Correctness Verification ---\n")

    results = {}

    # sum_bytes
    code = assemble_file(os.path.join(PROGRAMS_DIR, "sum_bytes.pa"))
    vm = VM()
    vm.load_program(code)
    vm.setup_memory(0x1000, bytes(range(1, 11)))
    vm.r[0] = 0x1000; vm.r[1] = 0; vm.r[2] = 10
    vm.run()
    results["sum_bytes"] = vm.r[1] == 55
    print(f"  sum_bytes: r1={vm.r[1]} (expected 55) {'OK' if vm.r[1] == 55 else 'FAIL'}")

    # find_zero
    code = assemble_file(os.path.join(PROGRAMS_DIR, "find_zero.pa"))
    vm = VM(); vm.load_program(code)
    data = bytearray([0x41] * 16); data[10] = 0
    vm.setup_memory(0x1000, bytes(data)); vm.r[0] = 0x1000
    vm.run()
    exp = 0x1000 + 10
    results["find_zero"] = vm.r[2] == exp
    print(f"  find_zero: r2=0x{vm.r[2]:x} (expected 0x{exp:x}) {'OK' if vm.r[2] == exp else 'FAIL'}")

    # xor_buffer
    code = assemble_file(os.path.join(PROGRAMS_DIR, "xor_buffer.pa"))
    vm = VM(); vm.load_program(code)
    data = bytes([0x10, 0x20, 0x30, 0x40])
    vm.setup_memory(0x1000, data); vm.r[0] = 0x1000; vm.r[1] = 0xAA; vm.r[2] = 4
    vm.run()
    ok = all(vm.mem[0x1000 + i] == (data[i] ^ 0xAA) for i in range(4))
    results["xor_buffer"] = ok
    print(f"  xor_buffer: {'OK' if ok else 'FAIL'}")

    # compare_bufs
    code = assemble_file(os.path.join(PROGRAMS_DIR, "compare_bufs.pa"))
    vm = VM(); vm.load_program(code)
    data = bytes(range(16))
    vm.setup_memory(0x1000, data); vm.setup_memory(0x2000, data)
    vm.r[0] = 0x1000; vm.r[1] = 0x2000; vm.r[2] = 1
    vm.run()
    results["compare_bufs"] = vm.r[0] == 0
    print(f"  compare_bufs (equal): r0={vm.r[0]} (expected 0) {'OK' if vm.r[0] == 0 else 'FAIL'}")

    # find_delim
    code = assemble_file(os.path.join(PROGRAMS_DIR, "find_delim.pa"))
    vm = VM(); vm.load_program(code)
    data = bytearray([0x41] * 16); data[12] = 0x3A
    vm.setup_memory(0x1000, bytes(data)); vm.r[0] = 0x1000; vm.r[1] = 0x3A; vm.r[2] = 1
    vm.run()
    exp = 0x1000 + 12
    results["find_delim"] = vm.r[2] == exp
    print(f"  find_delim: r2=0x{vm.r[2]:x} (expected 0x{exp:x}) {'OK' if vm.r[2] == exp else 'FAIL'}")

    # fibonacci
    fib_path = os.path.join(PROGRAMS_DIR, "fibonacci.pa")
    if os.path.exists(fib_path):
        code = assemble_file(fib_path)
        vm = VM(); vm.load_program(code)
        vm.r[0] = 0; vm.r[1] = 1; vm.r[2] = 10  # F(10)
        vm.run()
        # After fibonacci: r1 should have F(10). With a=r0, b=r1, after n iterations:
        # F(10) = 55, but our loop computes: start a=0,b=1, after 10 iters a=F(10),b=F(11)
        # Result is in r0 (a) after the swap pattern
        # Actually let's check: mv xK(r3=r1=b), ad xD(r1=r1+r0=a+b), mv! r0,r3(r0=old_b)
        # So after each iter: new_r1=a+b, new_r0=old_b. That means r0=F(k), r1=F(k+1)
        # After 10 iters starting from r0=0,r1=1: r0=F(10)=55, r1=F(11)=89
        results["fibonacci"] = vm.r[0] == 55
        print(f"  fibonacci: r0={vm.r[0]} (expected 55) {'OK' if vm.r[0] == 55 else 'FAIL'}")

    # min_byte
    min_path = os.path.join(PROGRAMS_DIR, "min_byte.pa")
    if os.path.exists(min_path):
        code = assemble_file(min_path)
        vm = VM(); vm.load_program(code)
        data = bytes([50, 30, 70, 10, 90])
        vm.setup_memory(0x1000, data)
        vm.r[0] = 0x1000; vm.r[2] = 5
        vm.run()
        results["min_byte"] = vm.r[1] == 10
        print(f"  min_byte: r1={vm.r[1]} (expected 10) {'OK' if vm.r[1] == 10 else 'FAIL'}")

    all_ok = all(results.values())
    print(f"\n  All correct: {'YES' if all_ok else 'NO'}")
    return all_ok


def print_external_results(results):
    """Print external kernel results grouped by classification."""
    print("\n" + "=" * 80)
    print("EXTERNAL KERNEL RESULTS — Generalization Test")
    print("=" * 80)

    x86_note = "assembled" if results[0]["x86_assembled"] else "estimated"

    # Group by classification
    groups = {"A": [], "B": [], "C": []}
    for r in results:
        cls = EXTERNAL_CLASSIFICATION.get(r["name"], "?")
        groups[cls].append(r)

    labels = {"A": "Class A — Fits Naturally", "B": "Class B — Fits With Friction",
              "C": "Class C — Does Not Fit"}

    print(f"\n{'Kernel':<20} {'Cls':>3} {'PA bc':>5} {'x86':>5} {'PA/x86':>6} | "
          f"{'Ext':>4} {'Cov':>5} {'B/I':>5}")
    print("-" * 80)

    for cls in ["A", "B", "C"]:
        if not groups[cls]:
            continue
        print(f"  {labels[cls]}")
        for r in groups[cls]:
            bc_x86 = r["pa_bytecode"] / r["x86_machine"] * 100 if r["x86_machine"] else 0
            ext_str = f"{r['extended']}" if r["extended"] else "-"
            bpi = r["pa_bytecode"] / r["pa_instr"] if r["pa_instr"] else 0
            name_short = r["name"].replace("ext_", "")
            print(f"  {name_short:<18} {cls:>3} {r['pa_bytecode']:>3}B {r['x86_machine']:>4}B {bc_x86:>5.0f}% | "
                  f"{ext_str:>4} {r['coverage']:>4.0f}% {bpi:>5.2f}")

    print("-" * 80)

    # Per-class summaries
    for cls in ["A", "B", "C"]:
        if not groups[cls]:
            continue
        total_pa = sum(r["pa_bytecode"] for r in groups[cls])
        total_x86 = sum(r["x86_machine"] for r in groups[cls])
        ratio = total_pa / total_x86 * 100 if total_x86 else 0
        total_ext = sum(r["extended"] for r in groups[cls])
        total_instr = sum(r["pa_instr"] for r in groups[cls])
        bpi = total_pa / total_instr if total_instr else 0
        print(f"  Class {cls} avg:       {cls:>3} {total_pa:>3}B {total_x86:>4}B {ratio:>5.0f}% | "
              f"{total_ext:>4} {'':>5} {bpi:>5.2f}")

    # Overall
    total_pa = sum(r["pa_bytecode"] for r in results)
    total_x86 = sum(r["x86_machine"] for r in results)
    total_instr = sum(r["pa_instr"] for r in results)
    ratio = total_pa / total_x86 * 100 if total_x86 else 0
    bpi = total_pa / total_instr if total_instr else 0
    print(f"\n  Overall external:  {'':>3} {total_pa:>3}B {total_x86:>4}B {ratio:>5.0f}% | "
          f"{'':>4} {'':>5} {bpi:>5.2f}")
    print(f"  x86 sizes: {x86_note}")

    # Classification distribution
    print(f"\n  Distribution: A={len(groups['A'])}, B={len(groups['B'])}, C={len(groups['C'])} "
          f"({len(results)} total)")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PA benchmark harness")
    parser.add_argument("--external", action="store_true", help="Run external kernels only")
    parser.add_argument("--all", action="store_true", help="Run original + external kernels")
    args = parser.parse_args()

    if args.external or args.all:
        ext_results = measure_external()
        print_external_results(ext_results)

    if not args.external:
        results = measure_sizes()
        print_results(results)
        verify_correctness()
