; Find first byte above threshold
; rdi = pointer, sil = threshold, rdx = length
; Returns: rax = pointer, or 0
BITS 64
loop:
  movzx eax, byte [rdi]
  cmp al, sil
  ja found
  inc rdi
  dec rdx
  jnz loop
  xor eax, eax
  ret
found:
  mov rax, rdi
  ret
