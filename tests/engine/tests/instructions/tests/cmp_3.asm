  .include "defs.asm"
main:
  li r0, 1
  cmp r0, r0
  int $INT_HALT