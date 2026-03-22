# External Kernel Corpus

## Purpose

Test PA's generalization on kernels not designed by the author and not used to derive the cell table. All kernels trace to production implementations in glibc, musl, or the Rust memchr/bytecount crates.

## Kernel List

| # | Kernel | Description | Provenance | Class | PA bc | x86 mc | PA/x86 |
|---|--------|-------------|-----------|-------|-------|--------|--------|
| K01 | memchr | Find first byte occurrence | glibc/musl/Rust | A | 20B | 53B | 38% |
| K02 | memcmp | Compare two buffers | glibc/musl | A | 22B | 27B | 81% |
| K03 | strchr | Find byte in null-terminated string | glibc/musl | B | 20B | 24B | 83% |
| K04 | strlen | Find first null byte | glibc/musl | A | 15B | 42B | 36% |
| K05 | find_nonascii | Find first byte > 127 | Rust is_ascii, simdutf8 | C | 18B | 32B | 56% |
| K06 | bytecount | Count byte occurrences | Rust bytecount crate | B | 31B | 21B | 148% |
| K07 | find_mismatch | Find first differing byte | diff/rsync | A | 24B | 61B | 39% |
| K08 | prefix_eq | Check if 16-byte prefixes match | HTTP/protocol parsers | A | 14B | 31B | 45% |
| K09 | find_byte_lt | Find first byte below threshold | Input validation | B | 18B | 23B | 78% |
| K10 | find_byte_gt | Find first byte above threshold | Binary detection | B | 18B | 23B | 78% |
| K11 | memrchr | Find last byte occurrence | glibc/Rust memrchr | C | 18B | 53B | 34% |
| K12 | memchr2 | Find first of two bytes | Rust memchr crate | B | 37B | 27B | 137% |
| K13 | strspn | Count leading bytes in accept set | glibc/musl | C | 34B | 23B | 148% |
| K14 | memset | Fill buffer with byte | glibc | B | 9B | 12B | 75% |

## Classification

### Class A — Fits Naturally (5 kernels)
memchr, memcmp, strlen, find_mismatch, prefix_eq

All use PA's core SIMD-scan pattern (gld + gcm/gcp + ffz) or simple scalar loops. Zero extended instructions. Average PA/x86 ratio: **44%**.

### Class B — Fits With Friction (6 kernels)
strchr, bytecount, find_byte_lt, find_byte_gt, memchr2, memset

Expressible in PA but with significant friction. Common issues: register shuffling via extended `mv!` (bytecount, memchr2), scalar-only paths where SIMD would be natural (memset), and dual-condition testing without predicate combine (strchr, memchr2). Average PA/x86 ratio: **102%**.

### Class C — Does Not Fit (3 kernels)
find_nonascii, memrchr, strspn

Core operations absent from PA: ordered vector compare / MSB extraction (find_nonascii), reverse bit scan (memrchr), set-membership testing (strspn). PA implementations are scalar fallbacks that lose all SIMD advantage.

## Coverage Summary

PA handles 5 of 14 external kernels naturally — the ones that match the vectorized equality-scan pattern (load chunk, compare, find first match). This pattern covers a meaningful subset of real-world byte-processing: memchr, memcmp, strlen, mismatch detection, and prefix matching.

6 kernels fit with friction, primarily due to missing predicate combining (can't OR two comparison results), limited register pair cells, and the lack of compact ordered comparison (addressed in v0.2).

3 kernels genuinely fall outside PA's scope. Set-membership (strspn) and MSB extraction (find_nonascii) require fundamentally different operations that PA's cell system cannot encode. These represent honest boundaries of the approach.

## Gap Analysis Inputs

The friction and failure points from this corpus directly drove the v0.2 ISA extensions. See [gap_analysis.md](gap_analysis.md) for the full frequency-based analysis and [v02_changes.md](v02_changes.md) for the resulting changes.
