  .data
  .type foo, int
  .int 0x0

  .text
main:
  li r0, &foo
  lw r1, r0
  li r2, 0xDEAD
  stb r0, r2
  int 0