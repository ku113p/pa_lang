; Check if first 16 bytes of two buffers match
; rdi = buf1, rsi = buf2
; Returns: eax = 0 (equal), 1 (not equal)
BITS 64
  movdqu xmm0, [rdi]
  movdqu xmm1, [rsi]
  pcmpeqb xmm0, xmm1
  pmovmskb eax, xmm0
  cmp eax, 0xFFFF
  sete al
  movzx eax, al
  xor eax, 1
  ret
