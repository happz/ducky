;
; Instruction sets
;
.def INST_SET_DUCKY: 0
.def INST_SET_MATH:  1


;
; Memory
;

.def PAGE_SIZE: 256
.def PAGE_MASK: 0xFF00

.def MM_OP_MPROTECT: 1
.def MM_OP_MTELL:    2
.def MM_OP_ALLOC:    3
.def MM_OP_FREE:     4
.def MM_OP_UNUSED:   5

.def MM_FLAG_READ:    0x0001
.def MM_FLAG_WRITE:   0x0002
.def MM_FLAG_EXECUTE: 0x0004
.def MM_FLAG_DIRTY:   0x0008

.def MM_FLAG_CS:      0x1000
.def MM_FLAG_DS:      0x2000

;
; Interrupts
;

.def IRQ_TIMER:     0
.def IRQ_KEYBOARD:  1

.def INT_HALT:    32
.def INT_BLOCKIO: 33
.def INT_VMDEBUG: 34
.def INT_MM:      35
.def INT_MATH:    36


;
; VMDebug Operations
;
.def VMDEBUG_LOGGER_VERBOSITY:  0

.def VMDEBUG_VERBOSITY_DEBUG:   0
.def VMDEBUG_VERBOSITY_INFO:    1
.def VMDEBUG_VERBOSITY_WARNING: 2
.def VMDEBUG_VERBOSITY_ERROR:   3


;
; BlockIO Operations
;
.def BLOCKIO_READ:  0
.def BLOCKIO_WRITE: 1


;
; Math Coprocessor Operations
;
.def MATH_LTOII:  9
.def MATH_INCL:   0
.def MATH_DECL:   1
.def MATH_ADDL:   2
.def MATH_SUBL:   3
.def MATH_MULL:   4
.def MATH_DIVL:   5
.def MATH_MODL:   6
.def MATH_ITOL:   7
.def MATH_LTOI:   8
.def MATH_IITOL: 10
.def MATH_DUPL:  11
.def MATH_UTOL:  12
.def MATH_SYMDIVL: 13
.def MATH_SYMMODL: 14


;
; IO ports
;

; Keyboard controller
.def PORT_KEYBOARD_IN:      0x0100

; TTY
.def PORT_TTY_OUT:          0x0200

; RTC
.def PORT_RTC_SECOND:       0x0300
