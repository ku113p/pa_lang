# PA Benchmark Results

## Summary

| Kernel | PA src | x86 src | Source ratio | PA bytecode | x86 machine | Bytecode ratio | PA instr | x86 instr |
|--------|--------|---------|-------------|-------------|-------------|---------------|----------|-----------|
| sum_bytes | 37B | 82B | 45% | 11B | 14B | 79% | 6 | 7 |
| find_zero | 61B | 160B | 38% | 16B | 28B | 57% | 8 | 11 |
| xor_buffer | 43B | 88B | 49% | 13B | 15B | 87% | 7 | 7 |
| compare_bufs | 78B | 195B | 40% | 22B | 38B | 58% | 12 | 14 |
| find_delim | 76B | 249B | 31% | 21B | 42B | 50% | 11 | 17 |
| **Average** | | | **41%** | | | **66%** | | |

**PA bytes/instruction (average): 1.89**

## Assessment vs Success Criteria

| Metric | Target | Acceptable | Actual | Verdict |
|--------|--------|------------|--------|---------|
| Source ratio (PA/x86) | ≤50% | ≤60% | 41% | **PASS (target)** |
| Bytes/instruction | ≤2.0 | ≤2.5 | 1.89 | **PASS (target)** |
| VM core LOC | ≤300 | ≤500 | 209 | **PASS (target)** |
| Compact cell coverage | ≥90% | ≥75% | ~91% | **PASS (target)** |
| Benchmark kernels | ≥4 | ≥3 | 5 | **PASS (target)** |

All five success criteria met at the target level (not just acceptable).

## Per-Kernel Analysis

### sum_bytes (scalar loop)
- Weakest source advantage (45%) — scalar ops are already terse in x86
- Bytecode ratio 79% — close to x86, as expected for simple scalar code
- Cell coverage: 100% compact (no extended instructions)

### find_zero (group + predicate)
- Strong source advantage (38%) — PA's group ops compress 3 x86 SIMD instructions into 2 PA instructions
- One extended instruction (ffz) breaks the 2-byte pattern
- This is PA's strongest demonstration kernel

### xor_buffer (scalar read-modify-write)
- Moderate advantage (49% source, 87% bytecode)
- PA and x86 have same instruction count (7)
- Bytecode advantage is smallest here — scalar kernels are PA's weakest case

### compare_bufs (group comparison)
- Strong source advantage (40%) — x86 needs splat setup, PA doesn't
- Good bytecode ratio (58%)
- Uses two vector registers (v0, v1) and vector-vector compare (pE cell)

### find_delim (group search)
- Strongest source advantage (31%) — x86 needs 4-instruction splat setup
- PA's `gcm pF` (compare against scalar register) handles this in one instruction
- Best demonstration of PA's scanning niche

## Methodology Caveats

- **Source size** measures raw UTF-8 bytes of code lines (excluding comments and blanks)
- **x86 machine code sizes** are manually estimated from instruction encoding tables, not assembled
- **PA bytecode sizes** are actual assembled output
- **No performance benchmarks** — PA runs in an interpreted Python VM; comparing execution speed against native x86 would be meaningless
- **Kernel selection** favors PA's strengths (scanning/probing patterns); PA would show less advantage on control-flow-heavy or arithmetic-heavy code
- **x86 reference** uses SSE2 for group operations; AVX2/AVX-512 comparisons might be different

## Correctness Verification

All 5 kernels pass correctness tests:
- sum_bytes: sum of [1..10] = 55
- find_zero: finds zero byte at position 10
- xor_buffer: correctly XORs each byte with key
- compare_bufs: correctly detects equal and unequal buffers
- find_delim: finds delimiter at position 12
