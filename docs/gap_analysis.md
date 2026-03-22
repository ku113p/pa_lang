# Phase 2: Gap Analysis Results

## Summary

- Kernels analyzed: 14 external + 7 original = 21 total
- External kernels graded A/B/C: 5/6/3
- Unique missing features identified: 12
- Gaps meeting 3-kernel threshold: 4

**Note**: Static frequency only (code occurrences). Dynamic frequency not measured — PA's primary metric is bytecode density, not runtime performance.

## Top Missing Abstractions (ranked by composite score)

| Rank | Missing Feature | Cat | Kernels | Instances | Byte Cost | Score | Rec |
|------|----------------|-----|---------|-----------|-----------|-------|-----|
| 1 | Compact ordered compare (cm in compact form) | G2 | 6 | 8 | 8B | 30 | EXTEND |
| 2 | Compact predicate extraction (ffz in compact form) | G9 | 5 | 5 | 5B | 22.5 | EXTEND |
| 3 | Conditional select (cmov/csel) | G7 | 4 | 4 | 16B | 24 | EXTEND |
| 4 | Additional register pair cells | G3 | 3 | 6 | 12B | 21 | EXTEND |
| 5 | Predicate OR/combine | G9 | 2 | 3 | 9B | 13.5 | DOCUMENT |
| 6 | No ordered vector compare | G6 | 3 | 3 | — | 12 | DOCUMENT |
| 7 | Missing immediate r3,#1 | G4 | 2 | 4 | 8B | 14 | DOCUMENT |
| 8 | No vector store | G6 | 1 | 1 | — | 3 | OUT OF SCOPE |
| 9 | No reverse bit scan (BSR) | G10 | 1 | 1 | — | 3 | OUT OF SCOPE |
| 10 | No set-membership operation | G1 | 1 | 1 | — | 3 | OUT OF SCOPE |
| 11 | No indexed addressing [base+index] | G5 | 1 | 1 | — | 3 | OUT OF SCOPE |
| 12 | Second-pointer memory cells | G5 | 2 | 4 | 4B | 12 | DOCUMENT |

### Score computation

```
score = (kernel_count × 3) + (instance_count × 1) + (byte_cost × 0.5)
```

**Sensitivity check**: Re-ranking with weights 2:1:1 and 5:1:0.5 — the top 4 gaps remain the same in all three weight sets (compact ordered compare, compact predicate extraction, conditional select, register pair cells). The ranking is robust.

## Per-Kernel Gap Sheets

### K01: ext_memchr (Class A)

**Instructions**: 11 (8 compact, 1 extended, 2 no-operand). **Bytecode**: 21B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G9 | ffz compact form | ffz! r2,p0 (3B) | +1B | bsf eax,eax |

**Notes**: Identical pattern to existing find_delim. Only friction is ffz! being extended (3B vs 2B compact).

---

### K02: ext_memcmp (Class A)

**Instructions**: 12 (10 compact, 0 extended, 2 no-operand). **Bytecode**: 22B.

No gaps. Clean fit using gld+gld+gcp pattern. All instructions compact.

---

### K03: ext_strchr (Class B)

**Instructions**: 11 (9 compact, 0 extended, 2 no-operand). **Bytecode**: 20B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G9 | Predicate OR (combine null + match) | Two separate scalar checks | +6B | por xmm0,xmm3 |
| 2 | G2 | Equality test without corruption | xr xK corrupts r3 | 0B (works but ugly) | cmp al,sil |

**Notes**: SIMD path (2 compares + predicate OR + ffz) would be ideal but PA lacks predicate combine. Scalar fallback uses xr xK which corrupts r3, acceptable since we reload next iteration. Uses 4 labels (@L0,@F0,@L1,@F1) consuming all branch targets.

---

### K04: ext_strlen (Class A)

**Instructions**: 8 (6 compact, 1 extended, 1 no-operand). **Bytecode**: 16B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G9 | ffz compact form | ffz! r2,p0 (3B) | +1B | bsf eax,eax |

**Notes**: Identical to find_zero without counter. Near-perfect fit.

---

### K05: ext_find_nonascii (Class C)

**Instructions**: 10 (7 compact, 1 extended, 2 no-operand). **Bytecode**: 19B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G2 | Compact ordered compare | cm! r3,r1 (3B) | +1B | cmp al,127 |
| 2 | G6 | Ordered vector compare | Scalar fallback (whole kernel) | ~20B vs SIMD | pmovmskb (no cmp needed!) |
| 3 | G4 | Set r1=127 compactly | Caller must pre-set | 0B (convention) | — |

**Notes**: The fundamental issue is that x86 pmovmskb extracts high bits without any compare — it's a bit-extraction, not a comparison. PA has no equivalent. Even adding ordered vector compare wouldn't fully close this gap. Class C because the core operation (MSB extraction) is absent.

---

### K06: ext_bytecount (Class B)

**Instructions**: 14 (9 compact, 4 extended, 1 no-operand). **Bytecode**: 31B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G3 | Register pair flexibility | 3× mv! per iteration to shuttle r1 | +9B | (registers freely addressable) |
| 2 | G4 | r3,#1 immediate | Can't increment r3 directly | +3B (route through r1) | inc ecx |
| 3 | G2 | Condition flag clobber by mv! | sb iK to re-test after mv! | +2B | (flags preserved across mov) |

**Notes**: Worst friction case. The combination of (a) mJ always loading into r3, (b) xr xK requiring r1 for target, and (c) no r3+=1 cell forces count through r1 with 3 extended mv! swaps per iteration. The sb iK workaround (re-test condition after mv! clobbers it) adds 2B.

---

### K07: ext_find_mismatch (Class A)

**Instructions**: 13 (10 compact, 1 extended, 2 no-operand). **Bytecode**: 25B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G9 | ffz compact form | ffz! r2,p0 (3B) | +1B | bsf eax,eax |

**Notes**: Clean dual-buffer compare with gld+gld+gcp+ffz. gcp sets mask where bytes differ, ffz finds first set bit = first mismatch. Only friction is extended ffz.

---

### K08: ext_prefix_eq (Class A)

**Instructions**: 8 (6 compact, 0 extended, 2 no-operand). **Bytecode**: 14B.

No gaps. Perfect fit for 16-byte prefix. Single-shot gld+gld+gcp.

---

### K09: ext_find_byte_lt (Class B)

**Instructions**: 10 (7 compact, 1 extended, 2 no-operand). **Bytecode**: 19B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G2 | Compact ordered compare | cm! r1,r3 (3B) | +1B | cmp al,sil |
| 2 | G6 | Ordered vector compare | Scalar-only loop | ~15B vs SIMD | pcmpgtb |

**Notes**: cm! works but costs 3B vs 2B for a compact cell. No SIMD path since gcm only does equality.

---

### K10: ext_find_byte_gt (Class B)

**Instructions**: 10 (7 compact, 1 extended, 2 no-operand). **Bytecode**: 19B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G2 | Compact ordered compare | cm! r3,r1 (3B) | +1B | cmp al,sil |
| 2 | G6 | Ordered vector compare | Scalar-only loop | ~15B vs SIMD | pcmpgtb |

**Notes**: Mirror of K09. Identical gap profile.

---

### K11: ext_memrchr (Class C)

**Instructions**: 10 (8 compact, 0 extended, 2 no-operand). **Bytecode**: 18B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G10 | Reverse bit scan (BSR) | Scalar byte-by-byte reverse scan | ~12B vs SIMD | bsr eax,eax |

**Notes**: Interestingly compact as scalar (18B, 1.80 bpi, 80% coverage, 0 extended). The friction is at the *algorithm* level — can't do SIMD reverse scan — not at the encoding level. All individual instructions encode compactly.

---

### K12: ext_memchr2 (Class B)

**Instructions**: 18 (11 compact, 4 extended, 3 no-operand). **Bytecode**: 37B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G9 | Predicate OR | Can't OR two predicate masks | +12B (scalar fallback) | por xmm0,xmm3 |
| 2 | G3 | xr with r4/r5 | mv! to save/restore, dual cm! for equality | +6B | cmp al,dl |
| 3 | G2 | Equality via dual cm! | 2× cm! (6B) instead of 1 compact eq (2B) | +4B | cmp al,dl |

**Notes**: Worst-case B kernel. Natural SIMD approach (2× pcmpeqb + por + pmovmskb) is blocked by missing predicate OR. Scalar fallback requires dual cm! to simulate equality for the second byte (no compact xr with extended register). Uses all 4 branch labels.

---

### K13: ext_strspn (Class C)

**Instructions**: 16 (10 compact, 4 extended, 2 no-operand). **Bytecode**: 34B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G1 | Set-membership test | Degenerate 1-byte accept set only | — | test byte [rsi+rcx],1 |
| 2 | G5 | Indexed addressing [base+index] | Not possible | — | [rsi+rcx] |
| 3 | G3 | Register shuffling | 3× mv! per iteration (same as bytecount) | +9B | — |
| 4 | G2 | Condition flag clobber | sb iK re-test workaround | +2B | — |

**Notes**: Only implements degenerate 1-byte accept set. General strspn is fundamentally unexpressible — requires either 256-byte lookup table with indexed addressing or multiple SIMD compares with predicate OR. Both are absent.

---

### K14: ext_memset (Class B)

**Instructions**: 5 (4 compact, 0 extended, 1 no-operand). **Bytecode**: 9B.

| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G6 | Vector store | Scalar byte-by-byte store | ~7B vs SIMD | movdqu [rdi],xmm0 |

**Notes**: Cleanest B kernel — zero extended instructions. Friction is purely algorithmic (no SIMD store path), not encoding-level.

---

## Original Kernels (supplementary)

### fibonacci (Negative)
| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G3 | r0,r3 register pair | mv! r0,r3 (3B) | +1B | mov eax,ecx |

### min_byte (Negative)
| # | Gap | Specific Feature | Workaround | Extra Bytes | x86 Equivalent |
|---|-----|-----------------|------------|-------------|----------------|
| 1 | G2 | Compact ordered compare | cm! r3,r1 (3B) | +1B | cmp cl,bl |
| 2 | G7 | Conditional select | branch + mv (4B) | +2B | cmovb eax,ecx |

---

## Gap Category Summary

### G1: Missing ALU Operations
- **Set-membership test**: 1 kernel (strspn). OUT OF SCOPE — fundamentally different computational model.

### G2: Missing Compare / Condition Modes
- **Compact ordered compare (cm)**: 6 kernels (find_nonascii, find_byte_lt, find_byte_gt, bytecount, memchr2, min_byte). **EXTEND** — highest-frequency gap. Promoting cm from extended-only to compact cell would save 1B per occurrence (6-8 occurrences across corpus).
- **Condition flag clobber by mv!**: 2 kernels (bytecount, strspn). DOCUMENT — design consequence, not encoding gap. Workaround (sb iK) is ugly but functional.

### G3: Missing Register Pair Cells
- **r0,r3 pair**: 1 kernel (fibonacci). Below threshold alone.
- **General register flexibility**: 3 kernels (bytecount, memchr2, strspn) need registers beyond r0-r3 compact range. **EXTEND** — adding 2-3 more register pair cells would reduce mv! shuffling.

### G4: Missing Immediate Values
- **r3,#1**: 2 kernels (bytecount, implicitly strspn). Below threshold.
- **r1,#127 / r1,#128**: 1 kernel (find_nonascii). Below threshold.

### G5: Missing Memory Addressing Forms
- **Second-pointer memory cells**: 2 kernels need ld from r1 base. Below threshold as standalone, but partially addressed by G3 register pair improvements.
- **Indexed addressing**: 1 kernel (strspn). OUT OF SCOPE.

### G6: Missing Vector / Group Operations
- **Ordered vector compare**: 3 kernels (find_nonascii, find_byte_lt, find_byte_gt). DOCUMENT — would require new opcode + SIMD semantics. High complexity vs benefit for current scope.
- **Vector store**: 1 kernel (memset). OUT OF SCOPE at current scope.

### G7: Missing Conditional Move / Select
- **Conditional select**: 4 kernels benefit (min_byte, find_byte_lt, find_byte_gt, memchr2 — branch-over-move patterns). **EXTEND** — new opcode `cs` would replace 4B branch-over-move with 2B conditional select.

### G8: Missing Branch / Control Flow Forms
- No significant gaps. The 4 branch targets (@L0,@F0,@L1,@F1) are sufficient for all kernels. strchr and memchr2 use all 4, but none need more.

### G9: Missing Predicate Combining Operations
- **Compact ffz (predicate extraction)**: 5 kernels (memchr, strlen, find_mismatch, + existing find_zero, find_delim). **EXTEND** — promoting ffz to compact would save 1B per occurrence.
- **Predicate OR**: 2 kernels (strchr, memchr2). Below threshold.

### G10: Missing Reverse / Bidirectional Scan
- **Reverse bit scan (BSR)**: 1 kernel (memrchr). OUT OF SCOPE at current scope.

---

## Confirmed vs Unconfirmed Pre-Identified Extensions

| Pre-Identified Extension | Confirmed? | Supporting Kernels | Notes |
|--------------------------|-----------|-------------------|-------|
| Predicate-result compact cells (ffz compact) | **YES** | memchr, strlen, find_mismatch, find_zero, find_delim | 5 kernels, strong justification |
| Richer comparison modes (ordered compare) | **YES** | find_nonascii, find_byte_lt, find_byte_gt, bytecount, memchr2, min_byte | 6 kernels, strongest gap |
| Conditional move/select | **YES** | min_byte, find_byte_lt, find_byte_gt, memchr2 | 4 kernels, clean encoding |
| Additional memory cells | **NO** | Only 2 kernels need second-pointer | Below 3-kernel threshold |
| Improved branch coverage | **NO** | No kernel exceeds 4 branch targets | Not needed |

**Surprises**: Register pair cells (G3) emerged as a significant gap not strongly anticipated in likely_extensions.md. The mv! condition-flag-clobber issue was also not anticipated.

---

## Out-of-Scope Gaps (with rationale)

| Gap | Why Out of Scope | Workaround |
|-----|-----------------|------------|
| Set-membership (G1) | Fundamentally different computational model. Would require lookup tables or multi-way compare — breaks OP CELL identity. | Degenerate 1-byte version with scalar loop |
| Indexed addressing (G5) | Requires new addressing mode in cell expansion format. Architectural change. | Not expressible; kernel (strspn) is Class C |
| Vector store (G6) | Only 1 kernel (memset). Below frequency threshold. | Scalar byte-by-byte store |
| Reverse bit scan (G10) | Only 1 kernel (memrchr). Below frequency threshold. | Scalar reverse iteration |
| Ordered vector compare (G6) | Would require new opcode + SIMD semantics. 3 kernels benefit but complexity is high for current scope. | Scalar cm! loop |

---

## Phase 3 Recommendations (priority order)

1. **Compact ordered compare cells** (c-family): Promote `cm` from extended-only to compact form. Add 4-6 cells covering common register pairs for unsigned byte comparison. Saves 1B per cm! occurrence. Justified by 6 kernels.

2. **Compact predicate extraction cells** (f-family): Add compact ffz cells (e.g., `fA` = ffz r2,p0). Saves 1B per ffz! occurrence. Justified by 5 kernels.

3. **Conditional select opcode** (`cs`): New opcode that conditionally moves based on condition flag. Reuses x-family cells. Replaces branch-over-move patterns (4B → 2B). Justified by 4 kernels.

4. **Additional register pair cells**: Add 2-3 commonly needed pairs (r0,r3; r2,r3; r3,r0) to reduce mv! shuffling. Justified by 3 kernels + original fibonacci.

**Total new cells**: ~12-15 (within 20-cell budget for v0.2).
**Expected impact**: Reduce extended instruction count across corpus by ~60%. Improve Class B kernel bytecode sizes by ~10-15%.
