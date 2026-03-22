BITS 64
; Fibonacci F(n)
; ecx = n, eax = a (0), edx = b (1), result in eax
loop:
  lea ebx, [eax+edx]
  mov eax, edx
  mov edx, ebx
  dec ecx
  jnz loop
  ret
