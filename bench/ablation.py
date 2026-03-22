#!/usr/bin/env python3
"""Cell ablation study — test robustness of PA's compact encoding.

Measures bytecode size impact of removing cell families or individual cells.
Analyzes assembled bytecode to count which instructions use which cells,
then computes the size increase if those cells were unavailable (falling
back to 3-byte extended encoding).
"""

import os
import sys
import random
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pa.assembler import assemble_file
from pa.isa import CELLS, CELL_BY_BYTE, OPCODE_BY_BYTE, OPCODES, ESCAPE_BYTES

PROGRAMS_DIR = os.path.join(os.path.dirname(__file__), "..", "programs")

ALL_KERNELS = [
    "sum_bytes", "find_zero", "xor_buffer", "compare_bufs", "find_delim",
    "fibonacci", "min_byte",
    "ext_memchr", "ext_memcmp", "ext_strchr", "ext_strlen",
    "ext_find_nonascii", "ext_bytecount", "ext_find_mismatch",
    "ext_prefix_eq", "ext_find_byte_lt", "ext_find_byte_gt",
    "ext_memrchr", "ext_memchr2", "ext_strspn", "ext_memset",
]


def analyze_cell_usage(bytecode):
    """Return list of (cell_name, cell_byte) for each compact instruction."""
    usage = []
    pc = 0
    while pc < len(bytecode):
        b = bytecode[pc]
        if b in ESCAPE_BYTES:
            pc += 3  # extended, no compact cell
        elif b in OPCODE_BY_BYTE:
            if OPCODES[OPCODE_BY_BYTE[b]][2]:
                cell_byte = bytecode[pc + 1]
                cell_name = CELL_BY_BYTE.get(cell_byte)
                if cell_name:
                    usage.append(cell_name)
                pc += 2
            else:
                pc += 1  # no-operand (rt)
        else:
            pc += 1
    return usage


def measure_ablation(removal_set, kernels=None):
    """Measure bytecode impact of removing cells.

    For each kernel, count compact instructions using removed cells.
    Each such instruction would grow by 1 byte (2B compact → 3B extended).

    Returns (baseline_total, ablated_total, per_kernel_details).
    """
    if kernels is None:
        kernels = ALL_KERNELS

    baseline_total = 0
    penalty_total = 0
    details = []

    for name in kernels:
        path = os.path.join(PROGRAMS_DIR, f"{name}.pa")
        if not os.path.exists(path):
            continue
        bytecode = assemble_file(path)
        baseline = len(bytecode)
        usage = analyze_cell_usage(bytecode)
        penalty = sum(1 for cell in usage if cell in removal_set)
        details.append({
            "name": name,
            "baseline": baseline,
            "penalty": penalty,
            "ablated": baseline + penalty,
        })
        baseline_total += baseline
        penalty_total += penalty

    return baseline_total, baseline_total + penalty_total, details


def cell_frequency():
    """Count how often each cell is used across all kernels."""
    freq = {}
    for name in ALL_KERNELS:
        path = os.path.join(PROGRAMS_DIR, f"{name}.pa")
        if not os.path.exists(path):
            continue
        bytecode = assemble_file(path)
        for cell in analyze_cell_usage(bytecode):
            freq[cell] = freq.get(cell, 0) + 1
    return freq


# --- Ablation Variants ---

FAMILY_VARIANTS = {
    "no_group":     {c for c in CELLS if c.startswith("g")},
    "no_predicate": {c for c in CELLS if c.startswith("p")},
    "half_imm":     {"iF", "iM", "iK", "iA"},
    "half_regpair": {"xG", "xK"},
    "no_memory":    {c for c in CELLS if c.startswith("m")},
    "no_branch":    {c for c in CELLS if c.startswith("q")},
    "no_compare":   {c for c in CELLS if c.startswith("c")},
    "no_ffz":       {c for c in CELLS if c.startswith("f")},
}

MINIMAL_KEEP = {"xA", "xD", "xF", "iB", "iI", "mE", "mJ", "gA", "qA", "qB"}


def run_family_ablations():
    """Run single-family removal variants."""
    print("\n" + "=" * 75)
    print("CELL ABLATION STUDY — Family Removal Variants")
    print("=" * 75)

    baseline, _, _ = measure_ablation(set())
    print(f"\nBaseline (all cells): {baseline}B")
    print(f"\n{'Variant':<18} {'Removed':>7} {'Ablated':>7} {'Increase':>8} {'%':>6}")
    print("-" * 55)

    for variant, removal in sorted(FAMILY_VARIANTS.items()):
        _, ablated, _ = measure_ablation(removal)
        inc = ablated - baseline
        pct = inc / baseline * 100
        print(f"{variant:<18} {len(removal):>5}c  {ablated:>5}B  {inc:>+5}B  {pct:>+5.1f}%")

    # Minimal
    removal = {c for c in CELLS if c not in MINIMAL_KEEP}
    _, ablated, _ = measure_ablation(removal)
    inc = ablated - baseline
    pct = inc / baseline * 100
    print(f"{'minimal_10':<18} {len(removal):>5}c  {ablated:>5}B  {inc:>+5}B  {pct:>+5.1f}%")

    # Empty
    removal = set(CELLS.keys())
    _, ablated, _ = measure_ablation(removal)
    inc = ablated - baseline
    pct = inc / baseline * 100
    print(f"{'empty_0':<18} {len(removal):>5}c  {ablated:>5}B  {inc:>+5}B  {pct:>+5.1f}%")


def run_single_cell_sweep():
    """Remove each cell individually, measure impact."""
    print("\n" + "=" * 75)
    print("SINGLE-CELL SWEEP — Per-Cell Contribution")
    print("=" * 75)

    baseline, _, _ = measure_ablation(set())
    results = []

    for cell in sorted(CELLS.keys()):
        _, ablated, _ = measure_ablation({cell})
        inc = ablated - baseline
        if inc > 0:
            results.append((cell, inc))

    results.sort(key=lambda x: -x[1])
    print(f"\n{'Cell':<6} {'Impact':>6} {'Expansion':<20}")
    print("-" * 40)
    for cell, inc in results:
        from pa.isa import CELL_EXPANSION_STR
        exp = CELL_EXPANSION_STR.get(cell, "?")
        print(f"{cell:<6} {inc:>+4}B   {exp:<20}")

    if not results:
        print("(no single cell removal has impact — all instructions use extended)")


def run_random_ablation(seed=42):
    """Random-N cell removal with repetitions."""
    print("\n" + "=" * 75)
    print("RANDOM-N CELL REMOVAL — Robustness Test")
    print("=" * 75)

    baseline, _, _ = measure_ablation(set())
    rng = random.Random(seed)
    all_cells = list(CELLS.keys())

    print(f"\nBaseline: {baseline}B")
    print(f"\n{'N':>3} {'Mean inc':>8} {'Stdev':>7} {'Min':>6} {'Max':>6} {'CV':>6}")
    print("-" * 45)

    for n in [5, 10, 15, 20]:
        if n > len(all_cells):
            continue
        increases = []
        for _ in range(10):
            removal = set(rng.sample(all_cells, n))
            _, ablated, _ = measure_ablation(removal)
            increases.append(ablated - baseline)

        mean = statistics.mean(increases)
        stdev = statistics.stdev(increases) if len(increases) > 1 else 0
        cv = stdev / mean * 100 if mean > 0 else 0
        print(f"{n:>3}  {mean:>+6.1f}B  {stdev:>5.1f}B  {min(increases):>+4}B  {max(increases):>+4}B  {cv:>5.1f}%")

        if n == 5 and cv > 15:
            print(f"  ⚠ CV > 15% at N=5 — encoding may be sensitive to cell selection")


def run_frequency_ordered():
    """Remove cells in ascending frequency order, measure cumulative impact."""
    print("\n" + "=" * 75)
    print("FREQUENCY-ORDERED PROGRESSIVE REMOVAL")
    print("=" * 75)

    freq = cell_frequency()
    baseline, _, _ = measure_ablation(set())

    # Sort by frequency ascending (least used first)
    ordered = sorted(freq.items(), key=lambda x: x[1])
    unused = [c for c in CELLS if c not in freq]

    print(f"\nBaseline: {baseline}B, {len(CELLS)} cells, {len(unused)} unused")
    print(f"\n{'Removed':>7} {'Cell':<6} {'Freq':>4} {'Total B':>7} {'Inc':>5} {'%':>6}")
    print("-" * 45)

    removed = set(unused)  # start by removing unused cells (0 impact)
    for cell, count in ordered:
        removed.add(cell)
        _, ablated, _ = measure_ablation(removed)
        inc = ablated - baseline
        pct = inc / baseline * 100
        print(f"{len(removed):>5}c   {cell:<6} {count:>4}  {ablated:>5}B  {inc:>+4}B  {pct:>+5.1f}%")


def run_adversarial():
    """Remove the 5 most-used cells."""
    print("\n" + "=" * 75)
    print("ADVERSARIAL REMOVAL — Top 5 Most-Used Cells")
    print("=" * 75)

    freq = cell_frequency()
    baseline, _, _ = measure_ablation(set())

    top5 = sorted(freq.items(), key=lambda x: -x[1])[:5]
    removal = {cell for cell, _ in top5}

    print(f"\nMost-used cells: {', '.join(f'{c}({n})' for c, n in top5)}")

    _, ablated, details = measure_ablation(removal)
    inc = ablated - baseline
    pct = inc / baseline * 100
    print(f"Baseline: {baseline}B → Ablated: {ablated}B ({inc:+}B, {pct:+.1f}%)")

    # Compare with random-5
    rng = random.Random(42)
    all_cells = list(CELLS.keys())
    random_incs = []
    for _ in range(10):
        r = set(rng.sample(all_cells, 5))
        _, ab, _ = measure_ablation(r)
        random_incs.append(ab - baseline)
    print(f"Random-5 mean: {statistics.mean(random_incs):+.1f}B")
    print(f"Adversarial-5 vs random-5: {inc / statistics.mean(random_incs):.1f}x worse")


if __name__ == "__main__":
    run_family_ablations()
    run_single_cell_sweep()
    run_random_ablation()
    run_frequency_ordered()
    run_adversarial()
