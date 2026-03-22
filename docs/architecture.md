# PA Architecture

## Overview

```
                    ┌─────────────┐
  .pa source  ───>  │  Assembler  │ ───>  bytecode bytes
                    │  (2-pass)   │
                    └─────────────┘
                          │
                    ┌─────┴─────┐
                    │           │
              ┌─────▼────┐ ┌───▼──────────┐
              │ Bytecode │ │ Disassembler │ ───> listing text
              │  Format  │ └──────────────┘
              │ (.pac)   │
              └─────┬────┘
                    │
              ┌─────▼────┐
              │    VM     │ ───> execution result
              │ (interp)  │
              └──────────┘
```

All components depend on `isa.py` for opcode and cell definitions.

## Instruction Encoding

### Compact Form (common case)
```
┌──────────┬──────────┐
│  opcode  │   cell   │
│  1 byte  │  1 byte  │
└──────────┴──────────┘
```

Most instructions are 2 bytes. The opcode identifies the operation, the cell identifies the operand pattern.

### Extended Form (escape prefix)
```
┌──────────┬──────────┬──────────┐
│  escape  │ sub-op   │ operand  │
│  1 byte  │  1 byte  │  1 byte  │
└──────────┴──────────┴──────────┘
```

Used for operations not covered by compact cells (e.g., `ffz r2,p0`).

### No-operand Form
```
┌──────────┐
│  opcode  │
│  1 byte  │
└──────────┘
```

Only `rt` (return) uses this form.

## Cell Expansion Mechanism

Cells are defined as tuples in `isa.py`:

```python
"xF": (0x02, ("reg", 1, "reg", 3))     # r1, r3
"mJ": (0x23, ("reg", 3, "mem", 0, 0))  # r3, [r0+0]
"pA": (0x40, ("preg", 0, "vreg", 0, "imm", 0x00))  # p0, v0, #00
```

The tagged tuple format lets the VM interpret operands generically without knowing which cell was used. Tags: `reg`, `imm`, `mem`, `vreg`, `preg`, `branch`.

## Assembler (Two-Pass)

### Pass 1: Label Collection
- Parse each line, skip comments (`;`) and blanks
- Labels (`@L0:`, `@F0:`) → record byte offset
- Instructions → compute size (1, 2, or 3 bytes) and advance offset

### Pass 2: Code Emission
- Look up opcode byte from `OPCODES` table
- Look up cell byte from `CELLS` table
- Branch cells (`q*`): resolve target label → compute signed relative offset
- Extended instructions (`ffz!`): emit escape byte + sub-opcode + packed operand

### Branch Resolution
Branch cells encode as signed byte offsets relative to the end of the branch instruction:
```
offset = target_address - (branch_address + 2)
```
Range: -128 to +127 bytes.

## VM Interpreter

### State
- `r[0..15]`: 64-bit scalar registers
- `v[0..7]`: 16-byte vector registers
- `p[0..7]`: 16-bit predicate masks
- `mem`: flat byte-addressable memory (1 MB default)
- `pc`: program counter
- `_condition`: boolean flag (set by ALU and group compare ops)

### Dispatch
Dict-based: opcode byte → handler method.

```python
handler = self._dispatch[opcode_byte]
handler()  # handler reads cell byte internally
```

### Condition Flag
All ALU operations set `_condition = (result != 0)`. Group compare operations set `_condition = (mask != 0)`. Branch instructions (`jn`, `jm`) test this flag.

This is a simplification for MVP. A production ISA would use explicit register operands in branch instructions.

### Group Operations
- `gld`: copies 16 bytes from memory into a vector register
- `gcm`: compares each byte lane against an immediate or scalar register, produces a 16-bit predicate mask
- `gcp`: compares two vector registers bytewise, produces a mismatch mask
- `ffz`: finds the index of the first set bit in a predicate mask

**The compare-mask-extract pattern**: Most scanning kernels follow a three-step pattern. Consider `find_zero` (find the first zero byte in a buffer):

1. `gld gA` — load 16 bytes from memory into vector register v0
2. `gcm pA` — compare each byte in v0 against 0x00, producing a 16-bit predicate mask in p0. Each bit records whether the corresponding byte matched.
3. `ffz fA` — find the index of the first set bit in p0. This gives the position of the first zero byte within the 16-byte chunk.

PA has no predicate OR instruction — you cannot combine two predicate masks (e.g., "byte is 0x0A OR byte is 0x0D"). This is why multi-value searches like memchr2 require awkward scalar fallbacks and fall into Class B.

## Bytecode Format (.pac)

```
Offset  Size  Field
0       4     Magic: "PA\x00\x01"
4       1     Flags: 0x00 (reserved)
5       1     Unused: 0x00
6       2     Code length (uint16 LE)
8       N     Code bytes
```

Maximum code size: 65,535 bytes.
