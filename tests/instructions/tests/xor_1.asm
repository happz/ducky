main:
  li r0, 0x00F0
  li r1, 0x0F0F
  xor r0, r1
  int 0
