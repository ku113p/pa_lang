BITS 64
; Compare two buffers (SSE2, 16 at a time)
; rdi = buf1, rsi = buf2, rdx = block count (len/16)
; result: eax = 0 equal, 1 not equal
loop:
  movdqu xmm0, [rdi]
  movdqu xmm1, [rsi]
  pcmpeqb xmm0, xmm1
  pmovmskb eax, xmm0
  cmp eax, 0xFFFF
  jne not_equal
  add rdi, 16
  add rsi, 16
  dec rdx
  jnz loop
  xor eax, eax
  ret
not_equal:
  mov eax, 1
  ret
