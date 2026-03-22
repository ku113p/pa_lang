; Fill buffer with byte (scalar)
; rdi = pointer, sil = byte, rdx = length
BITS 64
loop:
  mov byte [rdi], sil
  inc rdi
  dec rdx
  jnz loop
  ret
