; Find first null byte (strlen)
; rdi = pointer to string
; Returns: rax = length
; Uses SSE2
BITS 64
  mov rsi, rdi
  pxor xmm1, xmm1
loop:
  movdqu xmm0, [rdi]
  pcmpeqb xmm0, xmm1
  pmovmskb eax, xmm0
  test eax, eax
  jnz found
  add rdi, 16
  jmp loop
found:
  bsf eax, eax
  add rdi, rax
  sub rdi, rsi
  mov rax, rdi
  ret
