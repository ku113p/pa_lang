; Compare two buffers byte-by-byte (scalar for fair comparison)
; rdi = buf1, rsi = buf2, rdx = length
; Returns: eax = 0 if equal, nonzero if different
BITS 64
loop:
  movzx eax, byte [rdi]
  movzx ecx, byte [rsi]
  cmp al, cl
  jne diff
  inc rdi
  inc rsi
  dec rdx
  jnz loop
  xor eax, eax
  ret
diff:
  sub eax, ecx
  ret
