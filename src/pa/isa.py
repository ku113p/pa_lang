"""PA ISA definitions — opcodes, cells, and register classes.

All data is defined as plain dicts/tuples. No logic here, just tables.
"""

# ---------------------------------------------------------------------------
# Opcodes: mnemonic → (byte, category, needs_cell)
# ---------------------------------------------------------------------------

OPCODES: dict[str, tuple[int, str, bool]] = {
    # Scalar ALU
    "mv":  (0x10, "alu",   True),
    "ld":  (0x11, "mem",   True),
    "st":  (0x12, "mem",   True),
    "ad":  (0x13, "alu",   True),
    "sb":  (0x14, "alu",   True),
    "cs":  (0x15, "alu",   True),   # v0.2: conditional select
    "xr":  (0x17, "alu",   True),
    "cm":  (0x19, "alu",   True),   # v0.2: promoted from extended-only
    # Control flow
    "jm":  (0x1A, "flow",  True),
    "jn":  (0x1C, "flow",  True),
    "rt":  (0x1E, "flow",  False),
    # Group operations
    "gld": (0x20, "group", True),
    "gcm": (0x22, "group", True),
    "gcp": (0x23, "group", True),
    "ffz": (0x24, "group", True),   # v0.2: promoted from extended-only
}

OPCODE_BY_BYTE: dict[int, str] = {v[0]: k for k, v in OPCODES.items()}

# Escape opcodes (for extended instruction forms)
ESCAPES: dict[str, int] = {
    "ex0": 0xF0,  # scalar extended
    "ex1": 0xF1,  # memory extended
    "ex2": 0xF2,  # control-flow extended
    "ex3": 0xF3,  # group extended
}

ESCAPE_BYTES: set[int] = set(ESCAPES.values())

# ---------------------------------------------------------------------------
# Cell expansion types:
#   ("reg", dst, "reg", src)           — register pair
#   ("reg", dst, "imm", val)           — register + immediate
#   ("reg", dst, "mem", base, offset)  — register + memory access
#   ("vreg", v, "mem", base, size)     — vector + memory
#   ("preg", p, "vreg", v, "imm", val) — predicate compare vs immediate
#   ("preg", p, "vreg", v1, "vreg", v2) — predicate compare vs vector
#   ("preg", p, "vreg", v, "reg", r)  — predicate compare vs scalar
#   ("branch", direction, index)       — branch target
# ---------------------------------------------------------------------------

CELLS: dict[str, tuple[int, tuple]] = {
    # x* — Scalar pair cells
    "xA": (0x00, ("reg", 0, "reg", 1)),
    "xD": (0x01, ("reg", 1, "reg", 0)),
    "xF": (0x02, ("reg", 1, "reg", 3)),
    "xG": (0x03, ("reg", 2, "reg", 0)),
    "xK": (0x04, ("reg", 3, "reg", 1)),

    # i* — Tiny immediate cells
    "iA": (0x10, ("reg", 0, "imm", 0)),
    "iB": (0x11, ("reg", 0, "imm", 1)),
    "iF": (0x12, ("reg", 0, "imm", 16)),
    "iG": (0x13, ("reg", 1, "imm", 0)),
    "iH": (0x14, ("reg", 1, "imm", 1)),
    "iI": (0x15, ("reg", 2, "imm", 1)),
    "iK": (0x16, ("reg", 3, "imm", 0)),
    "iM": (0x17, ("reg", 1, "imm", 16)),

    # m* — Scalar memory cells
    "mA": (0x20, ("reg", 0, "mem", 0, 0)),
    "mE": (0x21, ("reg", 1, "mem", 0, 0)),
    "mG": (0x22, ("reg", 2, "mem", 0, 0)),
    "mJ": (0x23, ("reg", 3, "mem", 0, 0)),

    # g* — Group memory cells
    "gA": (0x30, ("vreg", 0, "mem", 0, 16)),
    "gD": (0x31, ("vreg", 1, "mem", 1, 16)),

    # p* — Predicate/compare cells
    "pA": (0x40, ("preg", 0, "vreg", 0, "imm", 0x00)),
    "pB": (0x41, ("preg", 0, "vreg", 0, "imm", 0xFF)),
    "pE": (0x42, ("preg", 0, "vreg", 0, "vreg", 1)),
    "pF": (0x43, ("preg", 0, "vreg", 0, "reg", 1)),

    # q* — Branch cells
    "qA": (0x50, ("branch", "back", 0)),
    "qB": (0x51, ("branch", "forward", 0)),
    "qC": (0x52, ("branch", "back", 1)),
    "qD": (0x53, ("branch", "forward", 1)),

    # --- v0.2 extensions (corpus-driven) ---

    # f* — Predicate-result extraction (compact ffz)
    "fA": (0x60, ("reg", 2, "preg", 0, "op", "ffz")),   # r2 = ffz(p0)
    "fB": (0x61, ("reg", 1, "preg", 0, "op", "ffz")),   # r1 = ffz(p0)

    # c* — Ordered compare cells (compact cm)
    "cA": (0x70, ("reg", 0, "reg", 1, "cmp", "ltu")),    # cond = r0 < r1
    "cB": (0x71, ("reg", 1, "reg", 3, "cmp", "ltu")),    # cond = r1 < r3
    "cC": (0x72, ("reg", 0, "reg", 1, "cmp", "gtu")),    # cond = r0 > r1
    "cD": (0x73, ("reg", 1, "reg", 3, "cmp", "gtu")),    # cond = r1 > r3
    "cE": (0x74, ("reg", 3, "reg", 1, "cmp", "ltu")),    # cond = r3 < r1
    "cF": (0x75, ("reg", 3, "reg", 1, "cmp", "gtu")),    # cond = r3 > r1

    # x* extension — Additional register pairs
    "xL": (0x05, ("reg", 0, "reg", 3)),                   # r0,r3
    "xM": (0x06, ("reg", 2, "reg", 3)),                   # r2,r3
    "xN": (0x07, ("reg", 3, "reg", 0)),                   # r3,r0
}

CELL_BY_BYTE: dict[int, str] = {v[0]: k for k, v in CELLS.items()}

# ---------------------------------------------------------------------------
# Human-readable cell expansions (for disassembler expanded mode)
# ---------------------------------------------------------------------------

CELL_EXPANSION_STR: dict[str, str] = {
    "xA": "r0,r1",   "xD": "r1,r0",   "xF": "r1,r3",
    "xG": "r2,r0",   "xK": "r3,r1",
    "xL": "r0,r3",   "xM": "r2,r3",   "xN": "r3,r0",
    "iA": "r0,#0",   "iB": "r0,#1",   "iF": "r0,#16",
    "iG": "r1,#0",   "iH": "r1,#1",   "iI": "r2,#1",
    "iK": "r3,#0",   "iM": "r1,#16",
    "mA": "r0,[r0+0]", "mE": "r1,[r0+0]", "mG": "r2,[r0+0]", "mJ": "r3,[r0+0]",
    "gA": "v0,[r0],16", "gD": "v1,[r1],16",
    "pA": "p0,v0,#00", "pB": "p0,v0,#FF",
    "pE": "p0,v0,v1",  "pF": "p0,v0,r1",
    "qA": "@L0",  "qB": "@F0",  "qC": "@L1",  "qD": "@F1",
    # v0.2 extensions
    "fA": "r2,p0",    "fB": "r1,p0",
    "cA": "r0<r1",    "cB": "r1<r3",    "cC": "r0>r1",
    "cD": "r1>r3",    "cE": "r3<r1",    "cF": "r3>r1",
}

# ---------------------------------------------------------------------------
# Branch label conventions
# ---------------------------------------------------------------------------

# Label name → (direction, index) mapping for assembler
LABEL_TARGETS: dict[str, tuple[str, int]] = {
    "@L0": ("back", 0),   "@F0": ("forward", 0),
    "@L1": ("back", 1),   "@F1": ("forward", 1),
}

# Branch cell → which label it resolves to
BRANCH_CELL_LABEL: dict[str, str] = {
    "qA": "@L0",  "qB": "@F0",
    "qC": "@L1",  "qD": "@F1",
}
