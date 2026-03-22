"""Two-pass line-based assembler for PA compact syntax.

Input: PA source text (compact form with OP CELL instructions).
Output: raw bytecode bytes.
"""

from pa.isa import OPCODES, CELLS, BRANCH_CELL_LABEL, ESCAPES


class AssemblyError(Exception):
    def __init__(self, line_num: int, message: str):
        super().__init__(f"line {line_num}: {message}")
        self.line_num = line_num


def _parse_lines(source: str) -> list[tuple[int, str]]:
    """Strip comments, blank lines. Return (original_line_num, stripped_text)."""
    result = []
    for i, raw in enumerate(source.splitlines(), 1):
        line = raw.split(";")[0].strip()
        if line:
            result.append((i, line))
    return result


def _is_label(text: str) -> bool:
    return text.startswith("@") and text.endswith(":")


def _instruction_size(mnemonic: str, cell_name: str | None) -> int:
    """Return byte size of an instruction."""
    if mnemonic == "rt":
        return 1
    if mnemonic == "ffz":
        # Extended: escape byte + sub-opcode + operand byte
        return 3
    return 2  # opcode + cell


def assemble(source: str) -> bytes:
    """Assemble PA source into bytecode bytes."""
    lines = _parse_lines(source)

    # --- Pass 1: collect labels, compute offsets ---
    labels: dict[str, int] = {}
    offsets: list[int] = []  # byte offset for each non-label line
    offset = 0

    instruction_lines: list[tuple[int, str, str, str | None]] = []

    for line_num, text in lines:
        if _is_label(text):
            label = text[:-1]  # strip trailing ':'
            if label in labels:
                raise AssemblyError(line_num, f"duplicate label: {label}")
            labels[label] = offset
            continue

        parts = text.split()
        mnemonic = parts[0].rstrip("!")  # strip '!' suffix (extended marker)
        cell_name = parts[1] if len(parts) > 1 else None

        if mnemonic not in OPCODES:
            raise AssemblyError(line_num, f"unknown mnemonic: {mnemonic}")
        if OPCODES[mnemonic][2] and cell_name is None and mnemonic != "ffz":
            raise AssemblyError(line_num, f"{mnemonic} requires a cell operand")

        size = _instruction_size(mnemonic, cell_name)
        instruction_lines.append((line_num, text, mnemonic, cell_name))
        offsets.append(offset)
        offset += size

    # --- Pass 2: emit bytecode ---
    code = bytearray()

    for idx, (line_num, text, mnemonic, cell_name) in enumerate(instruction_lines):
        op_byte = OPCODES[mnemonic][0]
        current_offset = offsets[idx]

        if mnemonic == "rt":
            code.append(op_byte)
            continue

        if mnemonic == "ffz":
            # Extended form: ex3 + ffz sub-opcode + operand encoding
            # For MVP: ffz always means "ffz r2,p0"
            # Encode as: ex3(0xF3) + 0x24(ffz) + 0x20 (r2=2, p0=0 packed)
            code.append(ESCAPES["ex3"])
            code.append(op_byte)
            # Operand byte: high nibble = dst scalar reg, low nibble = src pred reg
            # Parse extended operands if provided, otherwise default r2,p0
            operand_text = cell_name or ""
            parts = operand_text.split(",")
            if len(parts) == 2:
                dst_reg = int(parts[0].strip().lstrip("r"))
                src_preg = int(parts[1].strip().lstrip("p"))
            else:
                dst_reg, src_preg = 2, 0
            code.append((dst_reg << 4) | src_preg)
            continue

        if cell_name is None:
            raise AssemblyError(line_num, f"{mnemonic} requires a cell operand")

        # Branch cells need label resolution
        if cell_name.startswith("q"):
            if cell_name not in BRANCH_CELL_LABEL:
                raise AssemblyError(line_num, f"unknown branch cell: {cell_name}")
            target_label = BRANCH_CELL_LABEL[cell_name]
            if target_label not in labels:
                raise AssemblyError(line_num, f"unresolved label: {target_label}")
            target_offset = labels[target_label]
            # Relative offset from end of this instruction (current_offset + 2)
            rel = target_offset - (current_offset + 2)
            if rel < -128 or rel > 127:
                raise AssemblyError(line_num, f"branch target out of range: {rel}")
            code.append(op_byte)
            code.append(rel & 0xFF)  # signed byte as unsigned
            continue

        # Normal cell lookup
        if cell_name not in CELLS:
            raise AssemblyError(line_num, f"unknown cell: {cell_name}")
        code.append(op_byte)
        code.append(CELLS[cell_name][0])
        continue

    return bytes(code)


def assemble_file(path: str) -> bytes:
    """Read a .pa file and assemble it."""
    with open(path) as f:
        return assemble(f.read())
