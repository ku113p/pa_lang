; Find first occurrence of byte in buffer
; rdi = pointer, sil = byte to find, rdx = length
; Uses SSE2: splat byte, pcmpeqb, pmovmskb, bsf
BITS 64
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
  sub rdx, 16
  jnz loop
  xor eax, eax
  ret
found:
  bsf eax, eax
  add rax, rdi
  ret
