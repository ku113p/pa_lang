; Find first non-ASCII byte (high bit set)
; rdi = pointer, rsi = length
; Uses SSE2: pmovmskb extracts high bits directly — no compare needed
BITS 64
loop:
  movdqu xmm0, [rdi]
  pmovmskb eax, xmm0
  test eax, eax
  jnz found
  add rdi, 16
  sub rsi, 16
  jnz loop
  xor eax, eax
  ret
found:
  bsf eax, eax
  add rax, rdi
  ret
