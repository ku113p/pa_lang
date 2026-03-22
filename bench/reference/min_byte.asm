BITS 64
; Find minimum byte in buffer
; rdi = pointer, esi = count, result in al
  movzx eax, byte [rdi]
  inc rdi
  dec esi
loop:
  movzx ecx, byte [rdi]
  cmp cl, al
  cmovb eax, ecx
  inc rdi
  dec esi
  jnz loop
  ret
