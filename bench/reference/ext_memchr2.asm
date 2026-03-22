; Find first occurrence of either of two bytes
; rdi = pointer, sil = byte1, dl = byte2, rcx = length
; Returns: rax = pointer, or 0
BITS 64
loop:
  movzx eax, byte [rdi]
  cmp al, sil
  je found
  cmp al, dl
  je found
  inc rdi
  dec rcx
  jnz loop
  xor eax, eax
  ret
found:
  mov rax, rdi
  ret
