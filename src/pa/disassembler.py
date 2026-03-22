"""PA disassembler — bytecode to listing.

Supports compact mode (cell names) and expanded mode (operand expansion).
"""

from pa.isa import OPCODE_BY_BYTE, CELL_BY_BYTE, CELL_EXPANSION_STR, OPCODES, ESCAPE_BYTES


def disassemble(code: bytes, expanded: bool = False) -> str:
    """Disassemble bytecode into a text listing.

    Args:
        code: raw bytecode bytes
        expanded: if True, show operand expansions instead of cell names
    """
    lines: list[str] = []
    # First pass: find branch targets to insert labels
    branch_targets: dict[int, str] = _find_branch_targets(code)

    pc = 0
    while pc < len(code):
        # Insert label if this offset is a branch target
        if pc in branch_targets:
            lines.append(f"{branch_targets[pc]}:")

        op = code[pc]
        addr_prefix = f"  {pc:04x}: "

        if op in ESCAPE_BYTES:
            # Extended instruction
            if pc + 2 >= len(code):
                lines.append(f"{addr_prefix}??? (truncated extended)")
                break
            sub_op = code[pc + 1]
            operand = code[pc + 2]
            mnemonic = OPCODE_BY_BYTE.get(sub_op, f"?{sub_op:02x}")
            if mnemonic == "ffz":
                dst_reg = (operand >> 4) & 0x0F
                src_preg = operand & 0x0F
                if expanded:
                    lines.append(f"{addr_prefix}ffz r{dst_reg},p{src_preg}")
                else:
                    lines.append(f"{addr_prefix}ffz r{dst_reg},p{src_preg}")
            else:
                lines.append(f"{addr_prefix}{mnemonic} ext:{operand:02x}")
            pc += 3
            continue

        mnemonic = OPCODE_BY_BYTE.get(op)
        if mnemonic is None:
            lines.append(f"{addr_prefix}??? 0x{op:02x}")
            pc += 1
            continue

        needs_cell = OPCODES[mnemonic][2]
        if not needs_cell:
            lines.append(f"{addr_prefix}{mnemonic}")
            pc += 1
            continue

        if pc + 1 >= len(code):
            lines.append(f"{addr_prefix}{mnemonic} (truncated)")
            break

        cell_byte = code[pc + 1]

        # Branch instructions: cell byte is relative offset, not a cell ID
        if mnemonic in ("jm", "jn"):
            cell_name = CELL_BY_BYTE.get(cell_byte)
            if cell_name and cell_name.startswith("q"):
                # Was assembled with a cell — but the byte is a relative offset
                # We can't recover the cell name from a relative offset
                pass
            # Show as relative offset
            rel = cell_byte if cell_byte < 128 else cell_byte - 256
            target_addr = pc + 2 + rel
            target_label = branch_targets.get(target_addr, f"0x{target_addr:04x}")
            if expanded:
                lines.append(f"{addr_prefix}{mnemonic} {target_label}")
            else:
                lines.append(f"{addr_prefix}{mnemonic} {target_label}")
            pc += 2
            continue

        cell_name = CELL_BY_BYTE.get(cell_byte)
        if cell_name is None:
            lines.append(f"{addr_prefix}{mnemonic} ?{cell_byte:02x}")
            pc += 2
            continue

        if expanded:
            exp = CELL_EXPANSION_STR.get(cell_name, cell_name)
            lines.append(f"{addr_prefix}{mnemonic:<4} {exp}")
        else:
            lines.append(f"{addr_prefix}{mnemonic:<4} {cell_name}")

        pc += 2

    return "\n".join(lines)


def _find_branch_targets(code: bytes) -> dict[int, str]:
    """Scan bytecode for branch instructions, return {target_offset: label}."""
    targets: dict[int, str] = {}
    back_count = 0
    fwd_count = 0
    pc = 0

    while pc < len(code):
        op = code[pc]

        if op in ESCAPE_BYTES:
            pc += 3
            continue

        mnemonic = OPCODE_BY_BYTE.get(op)
        if mnemonic is None:
            pc += 1
            continue

        needs_cell = OPCODES[mnemonic][2]
        if not needs_cell:
            pc += 1
            continue

        if pc + 1 >= len(code):
            break

        if mnemonic in ("jm", "jn"):
            cell_byte = code[pc + 1]
            rel = cell_byte if cell_byte < 128 else cell_byte - 256
            target = pc + 2 + rel
            if target not in targets:
                if rel < 0:
                    targets[target] = f"@L{back_count}"
                    back_count += 1
                else:
                    targets[target] = f"@F{fwd_count}"
                    fwd_count += 1

        pc += 2

    return targets
