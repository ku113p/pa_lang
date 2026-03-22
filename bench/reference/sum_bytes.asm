; Sum bytes in buffer
; rdi = pointer, rsi = count, result in eax
  xor eax, eax
loop:
  movzx ecx, byte [rdi]
  add eax, ecx
  inc rdi
  dec rsi
  jnz loop
  ret
