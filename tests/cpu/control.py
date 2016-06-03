import logging
from six.moves import range

import ducky.cpu.coprocessor.control
import ducky.errors

from ducky.log import create_logger
from ducky.cpu.coprocessor.control import ControlRegisters
from ducky.util import F

from .. import common_run_machine, assert_raises, mock

def create_machine(ivt_address = None, pt_address = None, privileged = True, jit = False, **kwargs):
  machine_config = ducky.config.MachineConfig()

  if ivt_address is not None or pt_address is not None:
    machine_config.add_section('cpu')

    if ivt_address is not None:
      machine_config.set('cpu', 'ivt-address', ivt_address)

    if pt_address is not None:
      machine_config.set('cpu', 'pt-address', pt_address)

  machine_config.add_section('machine')
  machine_config.set('machine', 'jit', jit)

  M = common_run_machine(machine_config = machine_config, post_setup = [lambda _M: False], **kwargs)

  return M

def test_unprivileged():
  M = create_machine()
  core = M.cpus[0].cores[0]

  assert core.privileged is True

  core.control_coprocessor.read(ControlRegisters.CR0)

  core.privileged = False

  assert_raises(lambda: core.control_coprocessor.read(ControlRegisters.CR0), ducky.errors.AccessViolationError)

def test_cpuid():
  M = create_machine(cpus = 4, cores = 4)

  for i in range(0, 4):
    for j in range(0, 4):
      core = M.cpus[i].cores[j]
      core.privileged = True
      assert core.privileged is True

      cpuid_expected = 0xFFFFFFFF & ((i << 16) | j)
      cpuid_read = core.control_coprocessor.read(ControlRegisters.CR0)
      assert cpuid_expected == cpuid_read, 'CPUID mismatch: cpu=%i, core=%i, rcpu=%i, rcore=%i, expected=%i, read=%i' % (i, j, core.cpu.id, core.id, cpuid_expected, cpuid_read)

  assert_raises(lambda: M.cpus[0].cores[0].control_coprocessor.write(ControlRegisters.CR0, 0xFF), ducky.cpu.coprocessor.control.ReadOnlyRegisterError)

def test_ivt():
  M = create_machine(ivt_address = 0xC7C7DEAD)
  core = M.cpus[0].cores[0]

  core.privileged = True
  assert core.privileged is True, 'Core is not in privileged mode'

  v = core.control_coprocessor.read(ControlRegisters.CR1)
  assert v == 0xC7C7DEAD, F('IVT expected {expected:L}, {actual:L} found instead', expected = 0xC7C7DEAD, actual = v)

  core.control_coprocessor.write(ControlRegisters.CR1, 0xF5EEF00D)

  v = core.control_coprocessor.read(ControlRegisters.CR1)
  assert v == 0xF5EEF00D, F('IVT expected {expected:L}, {actual:L} found instead', expected = 0xF5EEF00D, actual = v)

def test_pt():
  M = create_machine(pt_address = 0xC7C7DEAD)
  core = M.cpus[0].cores[0]

  core.privileged = True
  assert core.privileged is True, 'Core is not in privileged mode'

  v = core.control_coprocessor.read(ControlRegisters.CR2)
  assert v == 0xC7C7DEAD, F('PT expected {expected:L}, {actual:L} found instead', expected = 0xC7C7DEAD, actual = v)

  core.control_coprocessor.write(ControlRegisters.CR2, 0xF5EEF00D)

  v = core.control_coprocessor.read(ControlRegisters.CR2)
  assert v == 0xF5EEF00D, F('PT expected {expected:L}, {actual:L} found instead', expected = 0xF5EEF00D, actual = v)

def test_jit():
  from ducky.cpu.coprocessor.control import CONTROL_FLAG_JIT

  def __check(jit_enable, expect_flag):
    M = create_machine(jit = jit_enable)
    core = M.cpus[0].cores[0]

    core.privileged = True
    assert core.privileged is True, 'Core is not in privileged mode'

    v = core.control_coprocessor.read(ControlRegisters.CR3)
    assert (v & CONTROL_FLAG_JIT) == expect_flag

    # Turn JIT on
    core.control_coprocessor.write(ControlRegisters.CR3, v | CONTROL_FLAG_JIT)
    w = core.control_coprocessor.read(ControlRegisters.CR3)
    assert (w & CONTROL_FLAG_JIT) == expect_flag

    # Turn JIT off
    core.control_coprocessor.write(ControlRegisters.CR3, v & ~CONTROL_FLAG_JIT)
    w = core.control_coprocessor.read(ControlRegisters.CR3)
    assert (w & CONTROL_FLAG_JIT) == expect_flag

  __check(True, CONTROL_FLAG_JIT)
  __check(False, 0)

def test_vmdebug():
  from ducky.cpu.coprocessor.control import CONTROL_FLAG_VMDEBUG

  def __check(vmdebug_enable, expect_flag):
    logger = create_logger(name = 'ducky-vmdebug-test', level = logging.DEBUG if vmdebug_enable else logging.INFO)
    M = create_machine(logger = logger)
    core = M.cpus[0].cores[0]

    core.privileged = True
    assert core.privileged is True, 'Core is not in privileged mode'

    v = core.control_coprocessor.read(ControlRegisters.CR3)
    assert (v & CONTROL_FLAG_VMDEBUG) == expect_flag

    # Test debug when enabled
    logger._log = mock.MagicMock()

    core.control_coprocessor.write(ControlRegisters.CR3, v | CONTROL_FLAG_VMDEBUG)
    w = core.control_coprocessor.read(ControlRegisters.CR3)
    assert (w & CONTROL_FLAG_VMDEBUG) == CONTROL_FLAG_VMDEBUG
    assert logger.getEffectiveLevel() == logging.DEBUG

    logger.debug('This should pass')
    logger._log.assert_any_call(logging.DEBUG, 'This should pass', tuple())

    # Test debug when disabled
    logger._log = mock.MagicMock()
    core.control_coprocessor.write(ControlRegisters.CR3, v & ~CONTROL_FLAG_VMDEBUG)
    w = core.control_coprocessor.read(ControlRegisters.CR3)
    assert (w & CONTROL_FLAG_VMDEBUG) == 0
    assert logger.getEffectiveLevel() == logging.INFO

    logger.debug('This should not pass')
    logger._log.assert_not_called()

  __check(True, CONTROL_FLAG_VMDEBUG)
  __check(False, 0)
