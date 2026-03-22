#!/usr/bin/env python3
"""PA benchmark harness — source and bytecode size comparisons."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pa.assembler import assemble_file
from pa.vm import VM

PROGRAMS_DIR = os.path.join(os.path.dirname(__file__), "..", "programs")
REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "reference")

KERNELS = [
    "sum_bytes",
    "find_zero",
    "xor_buffer",
    "compare_bufs",
    "find_delim",
]

# x86 machine code sizes (manually measured / estimated from assembled output)
X86_CODE_SIZES = {
    "sum_bytes": 14,      # 7 instructions
    "find_zero": 28,      # 10 instructions
    "xor_buffer": 15,     # 7 instructions
    "compare_bufs": 38,   # 14 instructions
    "find_delim": 42,     # 17 instructions (with splat setup)
}


def measure_sizes():
    results = []

    for name in KERNELS:
        pa_path = os.path.join(PROGRAMS_DIR, f"{name}.pa")
        asm_path = os.path.join(REFERENCE_DIR, f"{name}.asm")

        # PA source size
        with open(pa_path) as f:
            pa_source = f.read()
        pa_source_bytes = len(pa_source.encode("utf-8"))

        # PA source without comments/blanks
        pa_code_lines = [
            l.split(";")[0].strip()
            for l in pa_source.splitlines()
            if l.split(";")[0].strip() and not l.split(";")[0].strip().startswith(";")
        ]
        pa_code_only = "\n".join(pa_code_lines)
        pa_code_bytes = len(pa_code_only.encode("utf-8"))

        # PA bytecode size
        bytecode = assemble_file(pa_path)
        pa_bytecode_size = len(bytecode)

        # x86 asm source size
        with open(asm_path) as f:
            asm_source = f.read()
        asm_source_bytes = len(asm_source.encode("utf-8"))

        # x86 asm without comments/blanks
        asm_code_lines = [
            l.split(";")[0].strip()
            for l in asm_source.splitlines()
            if l.split(";")[0].strip() and not l.split(";")[0].strip().startswith(";")
        ]
        asm_code_only = "\n".join(asm_code_lines)
        asm_code_bytes = len(asm_code_only.encode("utf-8"))

        x86_machine = X86_CODE_SIZES.get(name, 0)

        # Count instructions
        pa_instr_count = sum(
            1 for l in pa_code_lines if not l.startswith("@")
        )
        asm_instr_count = sum(
            1 for l in asm_code_lines
            if not l.endswith(":") and l
        )

        results.append({
            "name": name,
            "pa_source": pa_source_bytes,
            "pa_code": pa_code_bytes,
            "pa_bytecode": pa_bytecode_size,
            "pa_instr": pa_instr_count,
            "asm_source": asm_source_bytes,
            "asm_code": asm_code_bytes,
            "asm_instr": asm_instr_count,
            "x86_machine": x86_machine,
        })

    return results


def verify_correctness():
    """Run each kernel with test data to verify it produces correct results."""
    print("\n--- Correctness Verification ---\n")

    results = {}

    # sum_bytes
    code = assemble_file(os.path.join(PROGRAMS_DIR, "sum_bytes.pa"))
    vm = VM()
    vm.load_program(code)
    data = bytes(range(1, 11))  # 1+2+...+10 = 55
    vm.setup_memory(0x1000, data)
    vm.r[0] = 0x1000
    vm.r[1] = 0
    vm.r[2] = 10
    vm.run()
    results["sum_bytes"] = vm.r[1] == 55
    print(f"  sum_bytes: r1={vm.r[1]} (expected 55) {'OK' if vm.r[1] == 55 else 'FAIL'}")

    # find_zero
    code = assemble_file(os.path.join(PROGRAMS_DIR, "find_zero.pa"))
    vm = VM()
    vm.load_program(code)
    data = bytearray([0x41] * 16)
    data[10] = 0
    vm.setup_memory(0x1000, bytes(data))
    vm.r[0] = 0x1000
    vm.run()
    expected = 0x1000 + 10
    results["find_zero"] = vm.r[2] == expected
    print(f"  find_zero: r2=0x{vm.r[2]:x} (expected 0x{expected:x}) {'OK' if vm.r[2] == expected else 'FAIL'}")

    # xor_buffer
    code = assemble_file(os.path.join(PROGRAMS_DIR, "xor_buffer.pa"))
    vm = VM()
    vm.load_program(code)
    data = bytes([0x10, 0x20, 0x30, 0x40])
    vm.setup_memory(0x1000, data)
    vm.r[0] = 0x1000
    vm.r[1] = 0xAA
    vm.r[2] = 4
    vm.run()
    ok = all(vm.mem[0x1000 + i] == (data[i] ^ 0xAA) for i in range(4))
    results["xor_buffer"] = ok
    print(f"  xor_buffer: {'OK' if ok else 'FAIL'}")

    # compare_bufs (equal)
    code = assemble_file(os.path.join(PROGRAMS_DIR, "compare_bufs.pa"))
    vm = VM()
    vm.load_program(code)
    data = bytes(range(16))
    vm.setup_memory(0x1000, data)
    vm.setup_memory(0x2000, data)
    vm.r[0] = 0x1000
    vm.r[1] = 0x2000
    vm.r[2] = 1
    vm.run()
    results["compare_bufs_eq"] = vm.r[0] == 0
    print(f"  compare_bufs (equal): r0={vm.r[0]} (expected 0) {'OK' if vm.r[0] == 0 else 'FAIL'}")

    # find_delim
    code = assemble_file(os.path.join(PROGRAMS_DIR, "find_delim.pa"))
    vm = VM()
    vm.load_program(code)
    data = bytearray([0x41] * 16)
    data[12] = 0x3A  # colon at position 12
    vm.setup_memory(0x1000, bytes(data))
    vm.r[0] = 0x1000
    vm.r[1] = 0x3A
    vm.r[2] = 1
    vm.run()
    expected = 0x1000 + 12
    results["find_delim"] = vm.r[2] == expected
    print(f"  find_delim: r2=0x{vm.r[2]:x} (expected 0x{expected:x}) {'OK' if vm.r[2] == expected else 'FAIL'}")

    all_ok = all(results.values())
    print(f"\n  All correct: {'YES' if all_ok else 'NO'}")
    return all_ok


def print_results(results):
    print("\n" + "=" * 80)
    print("PA BENCHMARK RESULTS — Source & Bytecode Size Comparison")
    print("=" * 80)

    # Table header
    print(f"\n{'Kernel':<16} {'PA src':>7} {'x86 src':>8} {'Ratio':>6} | "
          f"{'PA bc':>6} {'x86 mc':>7} {'Ratio':>6} | "
          f"{'PA #i':>5} {'x86 #i':>6}")
    print("-" * 80)

    for r in results:
        src_ratio = r["pa_code"] / r["asm_code"] * 100 if r["asm_code"] else 0
        bc_ratio = r["pa_bytecode"] / r["x86_machine"] * 100 if r["x86_machine"] else 0
        print(f"{r['name']:<16} {r['pa_code']:>5}B {r['asm_code']:>6}B {src_ratio:>5.0f}% | "
              f"{r['pa_bytecode']:>4}B {r['x86_machine']:>5}B {bc_ratio:>5.0f}% | "
              f"{r['pa_instr']:>5} {r['asm_instr']:>5}")

    # Averages
    avg_src = sum(r["pa_code"] / r["asm_code"] for r in results) / len(results) * 100
    avg_bc = sum(r["pa_bytecode"] / r["x86_machine"] for r in results if r["x86_machine"]) / len(results) * 100
    total_pa_bc = sum(r["pa_bytecode"] for r in results)
    total_pa_instr = sum(r["pa_instr"] for r in results)
    avg_bpi = total_pa_bc / total_pa_instr if total_pa_instr else 0

    print("-" * 80)
    print(f"{'Average':<16} {'':>7} {'':>8} {avg_src:>5.0f}% | "
          f"{'':>6} {'':>7} {avg_bc:>5.0f}% | ")
    print(f"\nPA bytes/instruction (avg): {avg_bpi:.2f}")
    print()

    # Assessment against criteria
    print("--- Assessment vs Success Criteria ---")
    print(f"  Source ratio target: ≤60%  →  actual: {avg_src:.0f}%  "
          f"{'PASS' if avg_src <= 60 else 'REVIEW' if avg_src <= 70 else 'FAIL'}")
    print(f"  Bytes/instruction target: ≤2.5  →  actual: {avg_bpi:.2f}  "
          f"{'PASS' if avg_bpi <= 2.5 else 'FAIL'}")
    print(f"  VM core LOC target: ≤500  →  see src/pa/vm.py")
    print()


if __name__ == "__main__":
    results = measure_sizes()
    print_results(results)
    verify_correctness()
