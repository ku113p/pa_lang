; Find byte in null-terminated string
; rdi = pointer, sil = byte to find
; Returns: rax = pointer to match, or 0 if not found
BITS 64
loop:
  movzx eax, byte [rdi]
  test al, al
  jz not_found
  cmp al, sil
  je found
  inc rdi
  jmp loop
not_found:
  xor eax, eax
  ret
found:
  mov rax, rdi
  ret
