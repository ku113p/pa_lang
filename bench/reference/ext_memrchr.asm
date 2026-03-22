; Find last occurrence of byte (reverse scan)
; rdi = pointer to one past end, sil = byte, rdx = length
; Uses SSE2: pcmpeqb + pmovmskb + BSR finds last match in 16-byte chunk
BITS 64
  movd xmm1, esi
  punpcklbw xmm1, xmm1
  pshuflw xmm1, xmm1, 0
  punpcklqdq xmm1, xmm1
loop:
  sub rdi, 16
  movdqu xmm0, [rdi]
  pcmpeqb xmm0, xmm1
  pmovmskb eax, xmm0
  test eax, eax
  jnz found
  sub rdx, 16
  jnz loop
  xor eax, eax
  ret
found:
  bsr eax, eax
  add rax, rdi
  ret
