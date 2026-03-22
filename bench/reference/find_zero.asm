; Find first zero byte (SSE2)
; rdi = pointer, result in rax
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
  add rax, rdi
  ret
