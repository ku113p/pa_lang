"""Tests for PA ISA data definitions."""

from pa.isa import OPCODES, OPCODE_BY_BYTE, CELLS, CELL_BY_BYTE, CELL_EXPANSION_STR


def test_opcode_bytes_unique():
    bytes_seen = {}
    for name, (byte, _, _) in OPCODES.items():
        assert byte not in bytes_seen, f"duplicate opcode byte 0x{byte:02x}: {name} and {bytes_seen[byte]}"
        bytes_seen[byte] = name


def test_cell_ids_unique():
    ids_seen = {}
    for name, (cell_id, _) in CELLS.items():
        assert cell_id not in ids_seen, f"duplicate cell ID 0x{cell_id:02x}: {name} and {ids_seen[cell_id]}"
        ids_seen[cell_id] = name


def test_reverse_lookups_complete():
    for name, (byte, _, _) in OPCODES.items():
        assert OPCODE_BY_BYTE[byte] == name

    for name, (cell_id, _) in CELLS.items():
        assert CELL_BY_BYTE[cell_id] == name


def test_all_cells_have_expansion_str():
    for name in CELLS:
        assert name in CELL_EXPANSION_STR, f"cell {name} missing from CELL_EXPANSION_STR"


def test_cell_expansions_well_formed():
    for name, (_, exp) in CELLS.items():
        assert isinstance(exp, tuple), f"cell {name} expansion is not a tuple"
        assert len(exp) >= 2, f"cell {name} expansion too short"


def test_opcode_count():
    assert len(OPCODES) == 14  # 13 MVP + cm (extended-only)
