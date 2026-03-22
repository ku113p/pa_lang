# What Changed in v0.2

## Motivation

v0.2 extends PA's ISA based on a corpus-driven gap analysis of 14 external kernels (not designed for PA). Every addition is justified by appearing in 3+ kernels. No speculative features.

## Changes

### 1. Compact Predicate Extraction (f-family)

`ffz` (find first set bit in predicate mask) was extended-only in v0.1 (3 bytes). It appears in every SIMD-scan kernel. v0.2 adds compact cells:

| Cell | Byte | Expansion |
|------|------|-----------|
| fA | 0x60 | r2 = ffz(p0) |
| fB | 0x61 | r1 = ffz(p0) |

**Impact**: 1B saved per scanning kernel (find_zero: 16→15B, find_delim: 21→20B, memchr: 21→20B, strlen: 16→15B, find_mismatch: 25→24B).

**Justified by**: 5 kernels using ffz in their inner loops.

### 2. Compact Ordered Compare (c-family)

`cm` (ordered byte comparison) was extended-only in v0.1. v0.2 adds compact cells:

| Cell | Byte | Expansion |
|------|------|-----------|
| cA | 0x70 | cond = (r0 < r1) unsigned |
| cB | 0x71 | cond = (r1 < r3) unsigned |
| cC | 0x72 | cond = (r0 > r1) unsigned |
| cD | 0x73 | cond = (r1 > r3) unsigned |
| cE | 0x74 | cond = (r3 < r1) unsigned |
| cF | 0x75 | cond = (r3 > r1) unsigned |

**Impact**: 1B saved per ordered comparison. Extended `cm!` remains for arbitrary register pairs.

**Justified by**: 6 kernels needing ordered comparison (find_byte_lt, find_byte_gt, find_nonascii, bytecount equality test, memchr2 dual-compare, min_byte).

### 3. Conditional Select (cs opcode)

New opcode `cs` at byte 0x15. If condition flag is true, performs the cell's register move; otherwise no-op. Does **not** update the condition flag.

Example: `cm cE; cs xF` — if r3 < r1, move r3 to r1 (branchless min).

**Impact**: Replaces `cm + jn + mv + label` (4 instructions, ~7B) with `cm + cs` (2 instructions, 4B). min_byte: 22→19B.

**Justified by**: 4 kernels using branch-over-move patterns.

### 4. Additional Register Pairs (x-family extension)

| Cell | Byte | Expansion |
|------|------|-----------|
| xL | 0x05 | r0,r3 |
| xM | 0x06 | r2,r3 |
| xN | 0x07 | r3,r0 |

**Impact**: Eliminates extended `mv!` in fibonacci (12→11B) and reduces register shuffling.

**Justified by**: 3 kernels needing register pairs outside the original 5-cell set.

## Summary

| Metric | v0.1 | v0.2 | Change |
|--------|------|------|--------|
| Opcodes | 14 | 15 | +1 (cs) |
| Compact cells | 27 | 38 | +11 |
| Encoding space used | 10.5% | 14.8% | +4.3% |
| Extended instructions (7 original kernels) | 4 | 0 | -4 |
| PA/x86 bytecode ratio (weighted) | 59% | 56% | -3pts |
| Bytes/instruction | 1.92 | 1.85 | -0.07 |

## What Was NOT Added

| Candidate | Why Not |
|-----------|---------|
| Predicate OR/AND | Only 2 kernels need it (below 3-kernel threshold) |
| Vector store | Only 1 kernel (memset) |
| Reverse bit scan (BSR) | Only 1 kernel (memrchr) |
| Set-membership | Only 1 kernel (strspn); fundamentally different model |
| Additional memory cells | Only 2 kernels need second-pointer access |
| Additional branch targets | No kernel exceeds current 4 branch targets |

## Backward Compatibility

v0.1 bytecode runs unchanged on the v0.2 VM. All new cells and opcodes occupy previously-unused encoding space. No existing byte values changed meaning.

v0.2 bytecode does **not** run on a v0.1 VM — new opcodes/cells will cause VMError. This is standard ISA extension behavior.
