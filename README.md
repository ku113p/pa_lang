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
- [Where PA Works Best](#where-pa-works-best)
- [Where PA Does Not Work Well](#where-pa-does-not-work-well)
- [Possible Deployment Directions](#possible-deployment-directions)
- [What Changed in v0.2](#what-changed-in-v02)
- [Key Findings](#key-findings)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Honest Interpretation](#honest-interpretation)
- [Why This Might Be Interesting](#why-this-might-be-interesting)
- [Why This Might Not Matter](#why-this-might-not-matter)
- [Document Guide](#document-guide)
- [Reproduce These Results](#reproduce-these-results)
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

- **Not a Wasm replacement** — Wasm has toolchains, runtimes, a formal spec, type safety, structured control flow, validation guarantees, and industry adoption
- **Not a general-purpose programming language** — 15 opcodes, 38 cells, no compiler
- **Not a claim about runtime performance** — the VM is interpreted Python
- **Not a claim about encoding superiority** — PA encodes fewer semantics per instruction than Wasm or JVM; smaller byte count does not mean "better"
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
ffz fA                      add rdi, 16
ad  xG                      jmp loop
rt                        found:
                             bsf eax, eax
8 instructions               add rax, rdi
15 bytes bytecode            ret
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
ffz fA     -->   ffz r2,p0
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
| `x*` | `xF` → `r1,r3` | Scalar register pair | 8 |
| `i*` | `iB` → `r0,#1` | Register + small immediate | 8 |
| `m*` | `mJ` → `r3,[r0+0]` | Scalar memory access | 4 |
| `g*` | `gA` → `v0,[r0],16` | Group/vector memory load | 2 |
| `p*` | `pA` → `p0,v0,#00` | Predicate compare | 4 |
| `q*` | `qA` → back target 0 | Local branch target | 4 |
| `f*` | `fA` → `r2,p0` | Predicate extraction (ffz) | 2 |
| `c*` | `cA` → `r0<r1` | Ordered compare | 6 |

38 cells total across 8 families, covering 21 benchmark kernels.

A **predicate** (`p*` family) is a comparison mask: compare 16 bytes against a target value, get a 16-bit result where each bit says "match" or "no match." The `ffz` instruction then finds the position of the first match. This compare-mask-extract pattern is how PA handles scanning operations.

## Try It

```bash
uv sync
uv run pytest tests/ -v              # 78 tests
uv run python bench/benchmark.py     # original kernel benchmarks
uv run python bench/benchmark.py --all  # original + external kernels
uv run python bench/ablation.py      # cell encoding robustness test

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

### Original Kernels (7)

| Kernel | PA bc | x86 mc | Wasm | PA/x86 | PA/Wasm |
|--------|-------|--------|------|--------|---------|
| find_zero | 15B | 33B | 40B | 45% | 38% |
| compare_bufs | 22B | 45B | 70B | 49% | 31% |
| find_delim | 20B | 52B | 64B | 38% | 31% |
| sum_bytes | 11B | 16B | 40B | 69% | 28% |
| xor_buffer | 13B | 16B | 41B | 81% | 32% |
| fibonacci | 11B | 13B | 42B | 85% | 26% |
| min_byte | 19B | 24B | 70B | 79% | 27% |

**Weighted averages**: PA/x86 = 56%, PA/Wasm = 30%, bytes/instruction = 1.85

*Note: PA bytecode encodes fewer semantics per instruction than Wasm. A Wasm instruction carries type, stack-effect, and validation information; PA's `ad xF` carries only "add these two registers." PA's smaller byte count reflects a simpler encoding, not a denser one.*

### External Kernels (14 — not designed for PA)

External kernels are classified by how naturally they fit PA's encoding: **Class A** (fits naturally, uses core scan patterns), **Class B** (expressible with friction — register shuffling, missing predicate OR for multi-value searches), **Class C** (core operations absent, outside PA's scope).

| Kernel | Class | PA bc | x86 mc | PA/x86 |
|--------|-------|-------|--------|--------|
| memchr | A | 20B | 53B | 38% |
| strlen | A | 15B | 42B | 36% |
| find_mismatch | A | 24B | 61B | 39% |
| prefix_eq | A | 14B | 31B | 45% |
| memcmp | A | 22B | 27B | 81% |
| strchr | B | 20B | 24B | 83% |
| find_byte_lt | B | 18B | 23B | 78% |
| find_byte_gt | B | 18B | 23B | 78% |
| memset | B | 9B | 12B | 75% |
| bytecount | B | 31B | 21B | 148% |
| memchr2 | B | 37B | 27B | 137% |
| find_nonascii | C | 18B | 32B | 56% |
| memrchr | C | 18B | 53B | 34% |
| strspn | C | 34B | 23B | 148% |

**Class A avg: 44%** | **Class B avg: 102%** | **Class C avg: 65%** | **Distribution: A=5, B=6, C=3**

Full results: [bench/results.md](bench/results.md)

## Where PA Works Best

PA's advantage is strongest on **vectorized equality-scan patterns**: load a 16-byte chunk, compare against a target byte or another chunk, find the first match. This pattern covers memchr, strlen, memcmp, find_mismatch, prefix matching, and delimiter scanning.

On these kernels, PA bytecode is 36-49% of x86 machine code. The cell system compresses the x86 SIMD setup sequence (movd + punpcklbw + pshuflw + punpcklqdq = 4 instructions, 16 bytes) into a single PA instruction (gcm pF = 2 bytes).

## Where PA Does Not Work Well

PA targets vectorized equality-scan patterns. The following categories fall outside this niche:

- **Ordered comparisons** (find_byte_lt, min/max): PA's condition flag is zero/nonzero only. Ordered compare requires v0.2's `cm` compact cells or extended `cm!`. Still scalar — no vectorized threshold scan.
- **Multi-condition scans** (strchr, memchr2): PA has no predicate OR. Scanning for two conditions simultaneously requires separate scalar checks.
- **Set-membership** (strspn): PA cannot express "is byte one of these N values." Requires fundamentally different operations (lookup tables, multi-way compare).
- **Reverse scanning** (memrchr): PA has only forward bit-scan (ffz/BSF). No reverse bit-scan (BSR equivalent).
- **Register pressure** (bytecount): The fixed cell-to-register mapping creates friction when operations need more than 4 active registers. Extended `mv!` shuffling adds 3 bytes per swap.

## Possible Deployment Directions

PA is an experiment, not a product. The following directions are plausible based on measured properties (bytecode density, interpreter footprint, kernel fit), not demonstrated deployments. No C implementation, no safety model, and no verifier exist yet.

- **Embeddable scanning filter**: PA's 1.85 B/instr density and tiny interpreter (~700 LOC) could suit a compact userspace filter VM for byte-level scanning — signature matching, delimiter detection, byte-stream classification. eBPF uses fixed 8-byte instructions prioritizing verifiability; PA trades safety guarantees for ~4x denser encoding in its narrow niche. *Gap: no C VM, no safety model, no integration test.*
- **Compact codegen target**: The 2-byte fixed encoding with 15 opcodes and 38 cells is a small, enumerable target for DSLs or code generators emitting scanning kernels. PA bytecode is 70% smaller than Wasm for equivalent kernels. *Gap: no compiler frontend exists.*
- **Research and teaching**: Complete reproducible implementation with ablation methodology, explicit negative results, and measured comparisons against x86 and Wasm. *Gap: not peer-reviewed, corpus is small.*

None of these are product plans. They are directions where the encoding density results suggest PA might be worth investigating further.

## What Changed in v0.2

v0.2 extends the ISA based on a [gap analysis](docs/gap_analysis.md) of 14 external kernels. Every addition justified by 3+ kernels:

- **Compact ffz** (f-family): Predicate extraction in 2 bytes instead of 3
- **Compact cm** (c-family): Ordered comparison in 2 bytes instead of 3
- **cs opcode**: Conditional select — branchless min/max patterns
- **More register pairs** (x-family): r0,r3 and r2,r3 added

Result: extended instructions eliminated from all 7 original kernels. Cell table grew from 27 to 38 (14.8% of encoding space). [Full details](docs/v02_changes.md).

## Key Findings

- **PA bytecode is 40-85% of x86 machine code** across 7 original kernels (weighted average 56%)
- **PA bytecode is 26-38% of Wasm instruction bytes** — PA is 70% smaller than Wasm
- **External kernels generalize**: 5/14 external kernels fit naturally (Class A, avg 44% PA/x86)
- **Honest boundaries**: 3/14 external kernels genuinely don't fit (Class C). bytecount and memchr2 are larger than x86 (148%, 137%)
- **Cell encoding is robust**: removing half the cells increases bytecode by only 6-7%. Full ablation (0 cells) increases by 34%. [Ablation study](docs/ablation.md)
- **Bytecode density is 1.85 bytes/instruction** — competitive with JVM (~1.8), denser than Wasm

## Design Decisions

- **Python**: fastest iteration for MVP; performance is not the claim
- **38 cells**: v0.1 cells derived from original kernels; v0.2 extensions derived from external corpus
- **Condition flag**: simplifies branch encoding vs explicit register-test operands
- **Dict dispatch**: simple, readable; performance difference negligible for ~15 opcodes
- **No JIT/optimizer/verifier**: validate the encoding idea first
- **Register-input parameters**: PA's calling convention naturally separates code templates from mutable parameters. A kernel like find_delim is a fixed 20-byte template that operates on whatever delimiter byte the caller loads into r1 — updating the delimiter requires no bytecode change. This property is inherent to the cell-based encoding, which keeps application-specific values out of the instruction stream

## Limitations

- Only 15 opcodes and 38 cells
- VM is interpreted Python — no performance claims
- No macro system, optimizer, or static verifier
- Cell table was derived from benchmark kernels (v0.1) and validated on external corpus (v0.2)
- Condition flag is a simplification (real ISA would use explicit register tests)
- Group ops are a small subset of real SIMD
- Branch range limited to signed byte (-128 to +127)
- x86 reference is hand-written assembly, not compiler output
- WAT is hand-written, not compiled from C/Rust

**Why the Python VM is not a fatal flaw**: PA's claims are about encoding density, not runtime speed. Bytecode sizes are measured from assembler output — a static property independent of VM implementation language. The Python VM exists to validate correctness (assembled bytecode runs and produces expected results). A C implementation would be needed before any performance claims, and none are made.

### Threats to Validity

- Benchmark suite is still small (~21 kernels)
- External kernels are author-implemented (even if not author-designed)
- Ablation tests cell removal, not cell re-derivation from an independent corpus
- Python VM precludes performance claims

## Honest Interpretation

The numbers are real — x86 sizes are assembled with NASM, Wasm sizes are compiled with wabt, PA bytecode is actual assembler output. The benchmark suite has grown from 7 to 21 kernels including 14 external kernels not designed for PA and 3 negative cases where PA performs poorly.

PA's bytecode density (1.85 B/instr) is genuinely competitive, but PA's ISA is far simpler than JVM or Wasm — it has no type system, no structured control flow, no validation. Comparing raw instruction bytes ignores the semantic density that Wasm carries per instruction. A single Wasm `i32.add` carries type, stack-effect, and validation information; PA's `ad xF` carries only "add these two registers."

The cell ablation study suggests the encoding captures genuine frequency patterns rather than arbitrary benchmark-specific mappings. But 21 kernels is still a small corpus, and the cell table was not derived independently of the benchmark suite.

## Why This Might Be Interesting

PA bytecode is 56% of assembled x86 machine code and 30% of Wasm instruction bytes. External kernels from glibc/musl confirm the scanning-pattern advantage generalizes (Class A kernels avg 44% PA/x86). The cell system is regular and learnable (8 families, consistent naming). The entire implementation is ~700 lines of Python. The combination of compact source, compact bytecode, and group operations is genuinely novel for a register-based VM.

## Why This Might Not Matter

PA could easily be dismissed as "just another custom bytecode with unusual syntax." There's no ecosystem, no adoption path, and no compelling deployment story. The cell system trades readability for compactness — most developers would rather write `add r1, r3`. Group ops are a strict subset of what SSE2/NEON already provide natively. Source compactness matters only if humans read/write the code; for compiler-generated bytecode, only binary density matters. And 6 of 14 external kernels show PA at parity or worse than x86 — the advantage is narrow.

## Document Guide

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | Internal design and encoding format |
| [docs/methodology.md](docs/methodology.md) | How measurements are taken |
| [docs/external_kernels.md](docs/external_kernels.md) | External kernel corpus and results |
| [docs/gap_analysis.md](docs/gap_analysis.md) | ISA gap analysis from external corpus |
| [docs/v02_changes.md](docs/v02_changes.md) | What changed in v0.2 and why |
| [docs/ablation.md](docs/ablation.md) | Cell encoding robustness testing |
| [bench/results.md](bench/results.md) | Full benchmark results with comparison |

## Reproduce These Results

```bash
uv sync
uv run pytest tests/ -v                       # 78 tests, all must pass
uv run python bench/benchmark.py --all         # full benchmark comparison
uv run python bench/ablation.py                # cell ablation test
```

## Next Steps

- C implementation of VM for actual performance benchmarks
- Additional scanning kernels (character class matching, protocol header parsing)
- Explore embedding as a sandboxed filter executor (BPF-like use case)
- Independent cell table derivation (derive cells from external corpus, test on original kernels)

## License

MIT
