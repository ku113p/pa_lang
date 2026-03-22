# PA — Packed Assembly

> What if assembly were optimized for compact symbolic encoding?

PA is an experimental compact assembly language and bytecode for a tiny register VM. It explores whether cell-based operand encoding can produce substantially smaller source and meaningfully smaller bytecode for tiny low-level kernels.

## Contents

- [Motivation](#motivation)
- [What PA Is](#what-pa-is)
- [What PA Is Not](#what-pa-is-not)
- [Quick Example](#quick-example)
- [How the Encoding Works](#how-the-encoding-works)
- [The Cell System](#the-cell-system)
- [Try It](#try-it)
- [Architecture](#architecture)
- [Benchmark Results](#benchmark-results)
- [Key Findings](#key-findings)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Honest Interpretation](#honest-interpretation)
- [Why This Might Be Interesting](#why-this-might-be-interesting)
- [Why This Might Not Matter](#why-this-might-not-matter)
- [Next Steps](#next-steps)

## Motivation

Assembly operands are verbose. `add r1, r3` repeats register patterns that appear across many programs. What if the most common operand patterns were compressed into single-token "cells"? PA tests this idea with a working assembler, bytecode format, and VM — then measures the results honestly.

## What PA Is

- A compact assembly-like language with cell-based operand encoding
- A 2-byte-per-instruction bytecode format (1 opcode byte + 1 cell byte)
- A register-based VM implemented in ~700 lines of Python
- An engineering experiment with measured results, not a production tool
- Especially suited to scanning/probing/byte-processing kernels

## What PA Is Not

- **Not a Wasm replacement** — Wasm has toolchains, runtimes, a formal spec, and industry adoption
- **Not a general-purpose programming language** — 14 opcodes, 27 cells, no compiler
- **Not a claim about runtime performance** — the VM is interpreted Python
- **Not a production tool or ecosystem** — this is a measured experiment
- **Not trying to replace x86, ARM, or any real ISA**

## Quick Example

**Find first zero byte in a buffer (16 bytes at a time):**

```
PA compact               x86 SSE2 (NASM)
─────────────            ──────────────────────────────
@L0:                       pxor xmm1, xmm1
gld gA                   loop:
gcm pA                     movdqu xmm0, [rdi]
jn  qB                     pcmpeqb xmm0, xmm1
ad  iF                     pmovmskb eax, xmm0
jm  qA                     test eax, eax
@F0:                        jnz found
ffz! r2,p0                  add rdi, 16
ad  xG                      jmp loop
rt                        found:
                             bsf eax, eax
8 instructions               add rax, rdi
16 bytes bytecode            ret
                           10 instructions, 33 bytes machine code
```

**The same kernel, expanded:**

```
Compact          Expanded
────────         ──────────────────
gld gA     -->   gld v0,[r0],16
gcm pA     -->   gcm p0,v0,#00
jn  qB     -->   jn  @F0
ad  iF     -->   ad  r0,#16
jm  qA     -->   jm  @L0
ffz r2,p0  -->   ffz r2,p0
ad  xG     -->   ad  r2,r0
rt         -->   rt
```

## How the Encoding Works

Most PA instructions are 2 bytes: one opcode byte and one cell byte.

```
Common instruction (2 bytes):
┌──────────┬──────────┐
│  opcode  │   cell   │
│  1 byte  │  1 byte  │
└──────────┴──────────┘

Example: "ad xF" encodes as  0x13 0x02
         opcode=ad(0x13)     cell=xF(0x02) → expands to r1,r3
```

Three encoding forms exist:
- **2-byte compact** (opcode + cell) — ~85% of instructions in benchmarks
- **3-byte extended** (escape + sub-opcode + operand) — for operations not in the cell table
- **1-byte** (`rt` only)

## The Cell System

Cells are compact symbolic operand templates. Each cell maps to a fixed operand pattern:

| Family | Example | Meaning | Count |
|--------|---------|---------|-------|
| `x*` | `xF` → `r1,r3` | Scalar register pair | 5 |
| `i*` | `iB` → `r0,#1` | Register + small immediate | 8 |
| `m*` | `mJ` → `r3,[r0+0]` | Scalar memory access | 4 |
| `g*` | `gA` → `v0,[r0],16` | Group/vector memory load | 2 |
| `p*` | `pA` → `p0,v0,#00` | Predicate compare | 4 |
| `q*` | `qA` → back target 0 | Local branch target | 4 |

27 cells total, covering all 7 benchmark kernels.

## Try It

```bash
uv sync
uv run pytest tests/ -v           # 42 tests
uv run python bench/benchmark.py  # full benchmark with Wasm + x86 comparison

# Assemble and disassemble
uv run python -c "
from pa.assembler import assemble_file
from pa.disassembler import disassemble
code = assemble_file('programs/find_zero.pa')
print(f'Bytecode: {len(code)} bytes')
print(disassemble(code, expanded=True))
"
```

## Architecture

```
src/pa/
├── isa.py           Data-driven opcode + cell definitions
├── assembler.py     Two-pass line-based assembler
├── bytecode.py      Binary format read/write
├── disassembler.py  Bytecode → compact/expanded listing
└── vm.py            Register VM, dict dispatch
```

```
.pa source  →  assembler  →  .pac bytecode  →  VM
(compact)      (two-pass)     (2 bytes/instr)    (register-based)
```

See [docs/architecture.md](docs/architecture.md) for internals.

## Benchmark Results

x86 sizes are **assembled** with NASM (`nasm -f bin`). Wasm sizes are instruction bytes only (code body, no module overhead). See [docs/methodology.md](docs/methodology.md).

### Scanning/Group Kernels (PA's strength)

| Kernel | PA bc | x86 mc | Wasm | PA/x86 | PA/Wasm |
|--------|-------|--------|------|--------|---------|
| find_zero | 16B | 33B | 40B | 48% | 40% |
| compare_bufs | 22B | 45B | 70B | 49% | 31% |
| find_delim | 21B | 52B | 64B | 40% | 33% |

### Scalar Kernels

| Kernel | PA bc | x86 mc | Wasm | PA/x86 | PA/Wasm |
|--------|-------|--------|------|--------|---------|
| sum_bytes | 11B | 16B | 40B | 69% | 28% |
| xor_buffer | 13B | 16B | 41B | 81% | 32% |

### Negative Cases (PA advantage diminished)

| Kernel | PA bc | x86 mc | Wasm | PA/x86 | PA/Wasm |
|--------|-------|--------|------|--------|---------|
| fibonacci | 12B | 13B | 42B | 92% | 29% |
| min_byte | 22B | 24B | 70B | 92% | 31% |

**Weighted averages**: PA/x86 = 59%, PA/Wasm = 32%, bytes/instruction = 1.92

Full results: [bench/results.md](bench/results.md)

## Key Findings

- **PA source is 42% of x86 asm** on average across all 7 kernels
- **PA bytecode is 59% of x86 machine code** (assembled, not estimated)
- **PA bytecode is 32% of Wasm instruction bytes** — PA is 68% smaller than Wasm
- **Scanning kernels show strongest advantage** (40-49% of x86) — group ops compress SIMD setup
- **Negative cases show PA at near-parity** with x86 (92%) — honest about where the advantage disappears
- **Bytecode density is 1.92 bytes/instruction** — competitive with JVM (~1.8), denser than Wasm

## Design Decisions

- **Python**: fastest iteration for MVP; performance is not the claim
- **27 cells**: derived from what benchmark kernels actually need, not speculative
- **Condition flag**: simplifies branch encoding vs explicit register-test operands
- **Dict dispatch**: simple, readable; performance difference negligible for ~14 opcodes
- **No JIT/optimizer/verifier**: validate the encoding idea first

## Limitations

- Only 14 opcodes and 27 cells (MVP subset)
- VM is interpreted Python — no performance claims
- No macro system, optimizer, or static verifier
- Cell table was derived from benchmark kernels (risk of overfitting)
- Extended instructions break the 2-byte pattern (appear in 4/7 kernels)
- Condition flag is a simplification (real ISA would use explicit register tests)
- Group ops are a small subset of real SIMD
- Branch range limited to signed byte (-128 to +127)
- x86 reference is hand-written assembly, not compiler output
- WAT is hand-written, not compiled from C/Rust

## Honest Interpretation

The numbers are real — x86 sizes are assembled with NASM, Wasm sizes are compiled with wabt, PA bytecode is actual assembler output. But the benchmark suite is small (7 kernels) and favors PA's niche (scanning/probing patterns).

Source compactness is measurable but trades readability for density. `ad xF` is objectively harder to read than `add r1, r3` for someone who hasn't learned the cell table. Whether this tradeoff is worthwhile depends on the use case.

PA's bytecode density (1.92 B/instr) is genuinely competitive, but PA's ISA is far simpler than JVM or Wasm — it has no type system, no structured control flow, no validation. Comparing raw instruction bytes ignores the semantic density that Wasm carries per instruction.

A fair summary: PA achieves meaningful compactness on the workloads it was designed for, with honest caveats about scope and methodology.

## Why This Might Be Interesting

The numbers exceed expectations. PA bytecode is 59% of assembled x86 machine code and 32% of Wasm instruction bytes. The cell system is regular and learnable (6 families, consistent naming). The entire implementation is ~700 lines of Python — validating that PA could be trivially embedded as a compact bytecode for scanning/probing filters (think BPF-like use case). The combination of compact source, compact bytecode, and group operations is genuinely novel for a register-based VM.

## Why This Might Not Matter

PA could easily be dismissed as "just another custom bytecode with unusual syntax." There's no ecosystem, no adoption path, and no compelling deployment story. The cell system trades readability for compactness — most developers would rather write `add r1, r3`. Group ops are a strict subset of what SSE2/NEON already provide natively. Source compactness matters only if humans read/write the code; for compiler-generated bytecode, only binary density matters.

## Next Steps

- C implementation of VM for actual performance benchmarks
- Additional scanning kernels (character class matching, protocol header parsing)
- Explore embedding as a sandboxed filter executor (BPF-like use case)
- Blog post / technical write-up

## License

MIT
