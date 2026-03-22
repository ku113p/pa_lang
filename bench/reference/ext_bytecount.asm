; Count occurrences of byte in buffer (scalar)
; rdi = pointer, sil = byte, rdx = length
; Returns: eax = count
BITS 64
  xor eax, eax
loop:
  movzx ecx, byte [rdi]
  cmp cl, sil
  jne skip
  inc eax
skip:
  inc rdi
  dec rdx
  jnz loop
  ret
