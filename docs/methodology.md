# Benchmark Methodology

## What Is Measured

Two dimensions of compactness:
1. **Source text size** — UTF-8 byte count of code lines
2. **Binary size** — assembled/compiled output in bytes

Runtime performance is **not** measured. PA runs in an interpreted Python VM; comparing execution speed against native x86 or compiled Wasm would be meaningless.

## How Source Size Is Counted

For all formats (PA, x86 asm, WAT):
- Count raw UTF-8 bytes of non-blank, non-comment lines
- Comments are stripped at the `;` character (PA, x86) or `;;` (WAT)
- Labels are included (they are part of what a programmer writes)
- Whitespace within lines is included
- The same method is applied to all formats

## How PA Bytecode Size Is Measured

The PA assembler (`pa.assembler.assemble()`) produces raw bytecode bytes. The size is `len(bytecode)` — instruction bytes only, excluding the 8-byte `.pac` container header (magic, flags, length fields).

## How x86 Machine Code Size Is Obtained

Each kernel's x86 reference (in `bench/reference/*.asm`) is assembled using NASM in flat binary mode:

```
nasm -f bin -o kernel.bin kernel.asm
```

The output file contains only raw machine code — no ELF headers, no section tables, no metadata. The file size equals the exact machine code byte count. All `.asm` files include a `BITS 64` directive for correct 64-bit instruction encoding.

If NASM is unavailable, the benchmark script falls back to hardcoded estimates (clearly marked as "estimated" in output).

## How Wasm Binary Size Is Obtained

WAT (WebAssembly Text Format) implementations of each kernel are compiled with:

```
wat2wasm kernel.wat -o kernel.wasm
```

Two measurements are reported:
- **Total .wasm size** — includes module header, type/function/export sections
- **Code body size** — instruction bytes only, extracted by parsing the code section and subtracting locals declarations and overhead

The "code body" measurement is used for comparison against PA bytecode, as it is the closest analog (instruction bytes only, no container overhead).

**Semantic density caveat**: Wasm instruction bytes carry more semantic weight per byte than PA bytecode. Each Wasm instruction encodes type information, stack effects, and validation metadata. PA instructions encode only the operation and operand pattern. The size comparison is a real measurement of byte counts, but the two formats encode different amounts of information per instruction. PA being smaller does not imply PA is "better" — it reflects a simpler encoding with fewer guarantees.

SIMD kernels use Wasm SIMD (128-bit, `v128.load`, `i8x16.eq`, `i8x16.bitmask`, etc.). Scalar kernels use standard Wasm instructions.

## What Is Excluded

- **Runtime performance** — PA's Python VM is for correctness verification only
- **Register allocation quality** — PA's cell system is a fixed mapping, not an allocator
- **Startup/loading overhead** — not relevant for kernel-level comparison
- **Compressed sizes** — gzip/zstd compression not measured

## Benchmark Selection and Known Biases

The 5 original kernels (sum_bytes, find_zero, xor_buffer, compare_bufs, find_delim) were chosen to exercise PA's target niche: byte scanning, probing, and grouped comparison. **This selection favors PA's strengths.**

Two negative cases (fibonacci, min_byte) were added to show where PA's advantage shrinks or disappears. These are scalar/arithmetic/comparison-heavy kernels outside PA's niche.

The x86 reference uses SSE2 for SIMD operations. AVX2 or AVX-512 equivalents might produce different results.

## Cell Table Bias

PA's 27 compact cells were derived from the benchmark kernels — cells were designed to fit the programs that test them. A general-purpose cell table would be larger, and compact cell coverage would likely decrease. This is acknowledged as a methodological limitation.

## Limitations

- Small benchmark suite (7 kernels)
- Cell table co-designed with benchmarks (risk of overfitting)
- No independent kernel authors
- Python VM precludes performance claims
- x86 reference is hand-written, not compiler-generated
- WAT is hand-written, not compiled from C/Rust
- No consideration of code alignment or padding effects
