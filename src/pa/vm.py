"""PA Virtual Machine — register-based interpreter with dict dispatch."""

from pa.isa import CELLS, CELL_BY_BYTE, ESCAPE_BYTES

MASK64 = (1 << 64) - 1


class VMError(Exception):
    pass


class VM:
    def __init__(self, mem_size: int = 1 << 20):
        self.r = [0] * 16                                  # scalar registers
        self.v = [bytearray(16) for _ in range(8)]         # vector registers
        self.p = [0] * 8                                   # predicate registers (16-bit masks)
        self.mem = bytearray(mem_size)
        self.code: bytes = b""
        self.pc = 0
        self.halted = False
        self._condition = False
        self._dispatch = {
            0x10: self._op_mv,
            0x11: self._op_ld,
            0x12: self._op_st,
            0x13: self._op_ad,
            0x14: self._op_sb,
            0x15: self._op_cs,   # v0.2: conditional select
            0x17: self._op_xr,
            0x19: self._op_cm,   # v0.2: compact ordered compare
            0x1A: self._op_jm,
            0x1C: self._op_jn,
            0x1E: self._op_rt,
            0x20: self._op_gld,
            0x22: self._op_gcm,
            0x23: self._op_gcp,
            0x24: self._op_ffz,  # v0.2: compact predicate extraction
        }

    def load_program(self, code: bytes) -> None:
        self.code = code
        self.pc = 0
        self.halted = False
        self._condition = False

    def setup_memory(self, address: int, data: bytes) -> None:
        self.mem[address:address + len(data)] = data

    def run(self, max_steps: int = 1_000_000) -> None:
        steps = 0
        while not self.halted and steps < max_steps:
            if self.pc >= len(self.code):
                raise VMError(f"pc {self.pc} out of bounds (code size {len(self.code)})")
            op = self.code[self.pc]
            self.pc += 1

            if op in ESCAPE_BYTES:
                self._exec_extended(op)
                steps += 1
                continue

            handler = self._dispatch.get(op)
            if handler is None:
                raise VMError(f"unknown opcode 0x{op:02x} at pc {self.pc - 1}")
            handler()
            steps += 1

        if steps >= max_steps:
            raise VMError(f"execution limit reached ({max_steps} steps)")

    def _read_cell(self) -> tuple:
        cell_byte = self.code[self.pc]
        self.pc += 1
        cell_name = CELL_BY_BYTE.get(cell_byte)
        if cell_name is None:
            raise VMError(f"unknown cell byte 0x{cell_byte:02x}")
        return CELLS[cell_name][1]

    def _read_cell_byte(self) -> int:
        b = self.code[self.pc]
        self.pc += 1
        return b

    # --- ALU operations (all set condition flag) ---

    def _alu_operands(self, exp: tuple) -> tuple[int, int]:
        if exp[0] == "reg" and exp[2] == "reg":
            return exp[1], self.r[exp[3]]
        if exp[0] == "reg" and exp[2] == "imm":
            return exp[1], exp[3]
        raise VMError(f"invalid ALU cell expansion: {exp}")

    def _op_mv(self):
        exp = self._read_cell()
        dst, val = self._alu_operands(exp)
        self.r[dst] = val & MASK64
        self._condition = self.r[dst] != 0

    def _op_ad(self):
        exp = self._read_cell()
        dst, val = self._alu_operands(exp)
        self.r[dst] = (self.r[dst] + val) & MASK64
        self._condition = self.r[dst] != 0

    def _op_sb(self):
        exp = self._read_cell()
        dst, val = self._alu_operands(exp)
        self.r[dst] = (self.r[dst] - val) & MASK64
        self._condition = self.r[dst] != 0

    def _op_xr(self):
        exp = self._read_cell()
        dst, val = self._alu_operands(exp)
        self.r[dst] = (self.r[dst] ^ val) & MASK64
        self._condition = self.r[dst] != 0

    def _op_cs(self):
        """v0.2: Conditional select — if condition, perform move; else no-op.
        Does NOT update condition flag."""
        exp = self._read_cell()
        if self._condition:
            dst, val = self._alu_operands(exp)
            self.r[dst] = val & MASK64
        # condition flag is NOT updated

    def _op_cm(self):
        """v0.2: Compact ordered compare — sets condition based on compare mode."""
        exp = self._read_cell()
        a_val = self.r[exp[1]] & 0xFF
        b_val = (self.r[exp[3]] if exp[2] == "reg" else exp[3]) & 0xFF
        mode = exp[5]
        if mode == "ltu":
            self._condition = a_val < b_val
        elif mode == "gtu":
            self._condition = a_val > b_val
        else:
            raise VMError(f"unknown compare mode: {mode}")

    def _op_ffz(self):
        """v0.2: Compact predicate extraction — find first set bit."""
        exp = self._read_cell()
        dst = exp[1]
        p_idx = exp[3]
        mask = self.p[p_idx]
        if mask == 0:
            self.r[dst] = 16
        else:
            self.r[dst] = (mask & -mask).bit_length() - 1

    # --- Memory operations ---

    def _op_ld(self):
        exp = self._read_cell()
        dst = exp[1]
        base = self.r[exp[3]]
        offset = exp[4]
        addr = (base + offset) & MASK64
        self.r[dst] = self.mem[addr]

    def _op_st(self):
        exp = self._read_cell()
        src = exp[1]
        base = self.r[exp[3]]
        offset = exp[4]
        addr = (base + offset) & MASK64
        self.mem[addr] = self.r[src] & 0xFF

    # --- Control flow ---

    def _op_jm(self):
        rel_byte = self._read_cell_byte()
        rel = rel_byte if rel_byte < 128 else rel_byte - 256
        self.pc += rel

    def _op_jn(self):
        rel_byte = self._read_cell_byte()
        rel = rel_byte if rel_byte < 128 else rel_byte - 256
        if self._condition:
            self.pc += rel

    def _op_rt(self):
        self.halted = True

    # --- Group operations ---

    def _op_gld(self):
        exp = self._read_cell()
        v_idx = exp[1]
        base = self.r[exp[3]]
        size = exp[4]
        for i in range(size):
            self.v[v_idx][i] = self.mem[(base + i) & MASK64]

    def _op_gcm(self):
        exp = self._read_cell()
        p_idx = exp[1]
        v_idx = exp[3]
        mask = 0
        if exp[4] == "imm":
            cmp_val = exp[5]
            for i in range(16):
                if self.v[v_idx][i] == cmp_val:
                    mask |= (1 << i)
        elif exp[4] == "reg":
            cmp_val = self.r[exp[5]] & 0xFF
            for i in range(16):
                if self.v[v_idx][i] == cmp_val:
                    mask |= (1 << i)
        self.p[p_idx] = mask
        self._condition = mask != 0

    def _op_gcp(self):
        exp = self._read_cell()
        p_idx = exp[1]
        v1_idx = exp[3]
        v2_idx = exp[5]
        mask = 0
        for i in range(16):
            if self.v[v1_idx][i] != self.v[v2_idx][i]:
                mask |= (1 << i)
        self.p[p_idx] = mask
        self._condition = mask != 0

    # --- Extended instructions ---

    def _exec_extended(self, escape_byte: int):
        if self.pc >= len(self.code):
            raise VMError("truncated extended instruction")
        sub_op = self.code[self.pc]
        self.pc += 1

        if self.pc >= len(self.code):
            raise VMError("truncated extended operand")
        operand = self.code[self.pc]
        self.pc += 1
        reg_a = (operand >> 4) & 0x0F
        reg_b = operand & 0x0F

        if sub_op == 0x24:  # ffz — find first zero/set bit in predicate
            mask = self.p[reg_b]
            if mask == 0:
                self.r[reg_a] = 16
            else:
                self.r[reg_a] = (mask & -mask).bit_length() - 1
        elif sub_op == 0x10:  # mv! — extended register-to-register move
            self.r[reg_a] = self.r[reg_b] & MASK64
            self._condition = self.r[reg_a] != 0
        elif sub_op == 0x19:  # cm! — unsigned byte compare, sets condition
            self._condition = (self.r[reg_a] & 0xFF) > (self.r[reg_b] & 0xFF)
        else:
            raise VMError(f"unknown extended sub-opcode 0x{sub_op:02x}")
