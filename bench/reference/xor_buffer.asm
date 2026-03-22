BITS 64
; XOR buffer with key byte
; rdi = pointer, esi = key, rdx = count
loop:
  movzx ecx, byte [rdi]
  xor ecx, esi
  mov byte [rdi], cl
  inc rdi
  dec rdx
  jnz loop
  ret
