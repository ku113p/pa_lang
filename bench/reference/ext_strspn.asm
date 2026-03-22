; Count leading bytes in accept set (lookup table approach)
; rdi = string (null-terminated), rsi = accept table (256 bytes, 1=accept)
; Returns count in rax
BITS 64
  xor eax, eax
loop:
  movzx ecx, byte [rdi]
  test cl, cl
  jz done
  test byte [rsi + rcx], 1
  jz done
  inc rdi
  inc eax
  jmp loop
done:
  ret
