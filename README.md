# PA — Packed Assembly

> What if assembly were optimized for compact symbolic encoding?

PA is a compact assembly-like language for a custom register-based VM. It's an engineering experiment exploring whether a "cell-based" operand notation can produce measurably shorter source and bytecode than conventional assembly — while remaining learnable and simple to implement.

**This is not** a production language, a Wasm competitor, or a general-purpose tool. It's a small, honest experiment with real numbers.

## Quick Example

**Find first zero byte in a buffer (16 bytes at a time):**

```
PA compact             x86 SSE2
─────────────          ──────────────────────────
@L0:                   loop:
gld gA                   movdqu xmm0, [rdi]
gcm pA                   pcmpeqb xmm0, xmm1
jn  qB                   pmovmskb eax, xmm0
ad  iF                   test eax, eax
jm  qA                   jnz found
@F0:                     add rdi, 16
ffz! r2,p0               jmp loop
ad  xG                 found:
rt                       bsf eax, eax
                         add rax, rdi
                         ret

8 instructions           10 instructions
16 bytes bytecode        ~28 bytes machine code
```

Each PA instruction is **OP CELL** — a 2-character mnemonic plus a compact operand template. `gld gA` means "group-load using cell gA", which expands to `gld v0,[r0],16`.

## Benchmark Results

| Kernel | PA source | x86 source | Ratio | PA bytecode | x86 machine | Ratio |
|--------|-----------|------------|-------|-------------|-------------|-------|
| sum_bytes | 37B | 82B | 45% | 11B | 14B | 79% |
| find_zero | 61B | 160B | 38% | 16B | 28B | 57% |
| xor_buffer | 43B | 88B | 49% | 13B | 15B | 87% |
| compare_bufs | 78B | 195B | 40% | 22B | 38B | 58% |
| find_delim | 76B | 249B | 31% | 21B | 42B | 50% |
| **Average** | | | **41%** | | | **66%** |

- **Source compactness**: PA source is 41% of x86 asm on average
- **Bytecode density**: 1.89 bytes/instruction average
- **All 5 kernels verified correct** via VM execution

See [bench/results.md](bench/results.md) for detailed analysis.

## How It Works

```
  .pa source    →    assembler    →    .pac bytecode    →    VM
  (compact)          (two-pass)        (2 bytes/instr)       (register-based)
```

1. Write PA source in compact `OP CELL` form
2. Assembler resolves labels and emits bytecode (1-byte opcode + 1-byte cell)
3. VM fetches, decodes cells to operand tuples, and executes

## The Cell System

Cells are compact symbolic operand templates. Each cell is a single token that maps to a fixed operand pattern:

| Family | Example | Meaning | Count |
|--------|---------|---------|-------|
| `x*` | `xF` → `r1,r3` | Scalar register pair | 5 |
| `i*` | `iB` → `r0,#1` | Register + small immediate | 8 |
| `m*` | `mJ` → `r3,[r0+0]` | Scalar memory access | 4 |
| `g*` | `gA` → `v0,[r0],16` | Group/vector memory load | 2 |
| `p*` | `pA` → `p0,v0,#00` | Predicate compare | 4 |
| `q*` | `qA` → back target 0 | Local branch target | 4 |

27 cells total, covering all 5 benchmark kernels. See [ref/cells.md](ref/cells.md) for the full table.

## Architecture

```
src/pa/
├── isa.py           Data-driven opcode + cell definitions     127 LOC
├── assembler.py     Two-pass line-based assembler             134 LOC
├── bytecode.py      Binary format read/write                   55 LOC
├── disassembler.py  Bytecode → compact/expanded listing       143 LOC
└── vm.py            Register VM, dict dispatch                209 LOC
                                                        Total: 668 LOC
```

See [docs/architecture.md](docs/architecture.md) for internals.

## Try It

```bash
# Setup
uv sync

# Run tests (38 tests)
uv run pytest tests/ -v

# Run benchmarks
uv run python bench/benchmark.py

# Assemble and disassemble a program
uv run python -c "
from pa.assembler import assemble_file
from pa.disassembler import disassemble
code = assemble_file('programs/find_zero.pa')
print(f'Bytecode: {len(code)} bytes')
print(disassemble(code))
print()
print('Expanded:')
print(disassemble(code, expanded=True))
"
```

## Design Decisions

- **Python**: fastest iteration for MVP; performance is not the goal
- **27 cells**: derived from what 5 benchmark kernels actually need, not speculative
- **Condition flag**: simplifies branch encoding vs explicit register-test operands
- **Dict dispatch**: simple, readable; performance difference negligible for 14 opcodes in Python
- **No JIT/optimizer/verifier**: MVP scope — validate the encoding idea first

## Limitations

- Only 14 opcodes and 27 cells implemented (MVP subset)
- VM is interpreted Python — not performance-competitive with native code
- No macro system, optimizer, or static verifier
- Condition flag is a simplification; a real ISA would use explicit register tests
- Group ops are a small subset of real SIMD (no arithmetic, no shuffles)
- Branch targets limited to signed byte range (-128 to +127)
- Extended instructions (ffz) break the clean 2-byte encoding

## Why This Might Not Matter

PA could easily be dismissed as "just another custom bytecode with unusual syntax." There's no ecosystem, no adoption path, and no compelling reason to use it over existing solutions for any real workload. The cell system trades readability for compactness — most developers would rather write `add r1, r3` than memorize that `xF` means `r1,r3`. The group operations are a strict subset of what SSE2/NEON already provide natively.

## Why This Might Be Interesting

The numbers are better than expected. PA source is 41% of x86 asm size — not marginal. Bytecode density at 1.89 bytes/instruction is competitive with the densest formats (JVM ~1.8, Wasm ~2.5). The cell system, while initially opaque, is regular and learnable — there are only 6 families with consistent naming. The total implementation is 668 lines of Python, which validates that the VM can be trivially embedded. For a niche use case — compact bytecode for scanning/probing kernels in an embedded filter VM (think BPF-like) — the combination of compact source, compact bytecode, and group operations is genuinely novel.

## License

MIT
