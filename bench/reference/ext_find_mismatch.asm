; Find first mismatching byte between two buffers
; rdi = buf1, rsi = buf2, rdx = length (multiple of 16)
; Returns: rax = offset of mismatch, or -1 if equal
; Uses SSE2
BITS 64
  mov rcx, rdi
loop:
  movdqu xmm0, [rdi]
  movdqu xmm1, [rsi]
  pcmpeqb xmm0, xmm1
  pmovmskb eax, xmm0
  xor eax, 0xFFFF
  jnz found
  add rdi, 16
  add rsi, 16
  sub rdx, 16
  jnz loop
  mov rax, -1
  ret
found:
  bsf eax, eax
  add rdi, rax
  sub rdi, rcx
  mov rax, rdi
  ret
