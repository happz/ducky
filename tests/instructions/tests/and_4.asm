  .include "defs.asm"
main:
  li r0, 0x0008
  and r0, 0x0004
  int $INT_HALT
