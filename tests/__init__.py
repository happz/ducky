import patch

import functools
import os
import sys
import unittest

import cpu.assemble
import cpu.registers
import console
import core
import machine
import mm
import util

def assert_registers(state, **regs):
  for i in range(0, cpu.registers.Registers.FLAGS):
    reg = 'r%i' % i
    val = regs.get(reg, 0)
    assert getattr(state, reg) == val, 'Register %s expected to have value %s (%s), %s (%s) found instead' % (reg, mm.UINT16_FMT(val), val, mm.UINT16_FMT(getattr(state, reg)), getattr(state, reg))

def assert_flags(state, **flags):
  assert state.flags.flags.privileged == flags.get('privileged', 1), 'PRIV flag expected to be %s' % flags.get('privileged', 1)
  assert state.flags.flags.e == flags.get('e', 0), 'E flag expected to be %s' % flags.get('e', 0)
  assert state.flags.flags.z == flags.get('z', 0), 'Z flag expected to be %s' % flags.get('z', 0)
  assert state.flags.flags.o == flags.get('o', 0), 'O flag expected to be %s' % flags.get('o', 0)
  assert state.flags.flags.s == flags.get('s', 0), 'S flag expected to be %s' % flags.get('s', 0)

def assert_mm(state, **cells):
  for addr, expected_value in cells.items():
    addr = util.str2int(addr)
    expected_value = util.str2int(expected_value)
    page_index = mm.addr_to_page(addr)
    page_offset = mm.addr_to_offset(addr)

    for page in state.mm_page_states:
      if page.index != page_index:
        continue

      real_value = mm.buff_to_uint16(page.content, page_offset)
      assert real_value.u16 == expected_value, 'Value at %s (page %s, offset %s) should be %s, %s found instead' % (mm.ADDR_FMT(addr), page_index, mm.UINT8_FMT(page_offset), mm.UINT16_FMT(expected_value), mm.UINT16_FMT(real_value))
      break

    else:
      assert False, 'Page %i (address %s) not found in memory' % (page_index, mm.ADDR_FMT(addr))

def run_machine(code, coredump_file = None, **kwargs):
  M = machine.Machine()

  if not hasattr(util, 'CONSOLE'):
    util.CONSOLE = console.Console(M, None, sys.stdout)
    util.CONSOLE.boot()
    util.CONSOLE.set_quiet_mode(True)

  M.hw_setup(**kwargs)

  sections = cpu.assemble.translate_buffer(code)

  csr, dsr, sp, ip, symbols = M.memory.load_raw_sections(sections)
  M.init_states.append((csr, dsr, sp, ip, False))
  M.binaries.append((csr, dsr, sp, ip, symbols))

  M.boot()
  M.run()
  M.wait()

  state = core.VMState.capture_vm_state(M)

  if coredump_file:
    state.save(coredump_file)

  return state

common_machine_run = functools.partial(run_machine, cpus = 1, cores = 1, irq_routines = 'instructions/interrupts-basic.bin')
