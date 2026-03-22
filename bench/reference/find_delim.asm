; Find first delimiter byte (SSE2)
; rdi = pointer, esi = delimiter, rdx = block count
; result: rax = address or 0 if not found
  movd xmm1, esi
  punpcklbw xmm1, xmm1
  pshuflw xmm1, xmm1, 0
  punpcklqdq xmm1, xmm1
loop:
  movdqu xmm0, [rdi]
  pcmpeqb xmm0, xmm1
  pmovmskb eax, xmm0
  test eax, eax
  jnz found
  add rdi, 16
  dec rdx
  jnz loop
  xor eax, eax
  ret
found:
  bsf eax, eax
  add rax, rdi
  ret
