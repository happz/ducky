"""
Block IO - persistent storage support.

Several different persistent storages can be attached to a virtual machine, each
with its own id. This module provides methods for manipulating their content. By
default, storages operate with blocks of constant, standard size, though this is
not a mandatory requirement - storage with different block size, or even with
variable block size can be implemented.

Each block has its own id. Block IO operations read or write one or more blocks to
or from a device. IO is requested by invoking the virtual interrupt, with properly
set values in registers.
"""

import os

from . import machine

from .cpu.registers import Registers
from .irq import InterruptList
from .irq.virtual import VirtualInterrupt, VIRTUAL_INTERRUPTS
from .mm import segment_addr_to_addr
from .util import debug

#: Size of block, in bytes.
BLOCK_SIZE = 1024

class StorageAccessError(Exception):
  """
  Base class for storage-related exceptions.
  """

  pass

class Storage(machine.MachineWorker):
  """
  Base class for all block storages.

  :param ducky.machine.Machine machine: machine storage is attached to.
  :param int sid: id of storage.
  :param int size: size of storage, in bytes.
  """

  def __init__(self, machine, sid, size):
    super(Storage, self).__init__()

    self.machine = machine
    self.id = sid
    self.size = size

  def do_read_block(self, src, dst, cnt):
    """
    Read one or more blocks from device to memory.

    Child classes are supposed to reimplement this particular method.

    :param u16 src: block id of the first block
    :param u24 dst: destination buffer address
    :param int cnt: number of blocks to read
    """

    pass

  def do_write_block(self, src, dst, cnt):
    """
    Write one or more blocks from memory to device.

    Child classes are supposed to reimplement this particular method.

    :param u24 src: source buffer address
    :param uin16 dst: block id of the first block
    :param int cnt: number of blocks to write
    """

    pass

  def read_block(self, src, dst, cnt):
    """
    Read one or more blocks from device to memory.

    Child classes should not reimplement this method, as it provides checks
    common for (probably) all child classes.

    :param u16 src: block id of the first block
    :param u24 dst: destination buffer address
    :param int cnt: number of blocks to read
    """

    debug('read_block: id=%s, src=%s, dst=%s, cnt=%s', self.id, src, dst, cnt)

    if (src + cnt) * BLOCK_SIZE > self.size:
      raise StorageAccessError('Out of bounds access: storage size %s is too small' % self.size)

    self.do_read_block(src, dst, cnt)

  def write_block(self, src, dst, cnt):
    """
    Write one or more blocks from memory to device.

    Child classes should not reimplement this method, as it provides checks
    common for (probably) all child classes.

    :param u24 src: source buffer address
    :param uin16 dst: block id of the first block
    :param int cnt: number of blocks to write
    """

    debug('write_block: id=%s, src=%s, dst=%s, cnt=%s', self.id, src, dst, cnt)

    if (dst + cnt) * BLOCK_SIZE > self.size:
      raise StorageAccessError('Out of bounds access: storage size %s is too small' % self.size)

    self.do_write_block(src, dst, cnt)

class FileBackedStorage(Storage):
  """
  Storage that saves its content into a regular file.
  """

  def __init__(self, machine, sid, path):
    """
    :param machine.Machine machine: virtual machine this storage is attached to
    :param int sid: storage id
    :param path: path to a underlying file
    """

    st = os.stat(path)

    super(FileBackedStorage, self).__init__(machine, sid, st.st_size)

    self.path = path
    self.file = None

  def boot(self):
    self.file = open(self.path, 'r+b')

  def halt(self):
    debug('BIO: halt')

    self.file.flush()
    self.file.close()

  def do_read_block(self, src, dst, cnt):
    debug('do_read_block: src=%s, dst=%s, cnt=%s', src, dst, cnt)

    self.file.seek(src * BLOCK_SIZE)
    buff = self.file.read(cnt * BLOCK_SIZE)

    for c in buff:
      self.machine.memory.write_u8(dst, ord(c))
      dst += 1

    debug('BIO: %s bytes read from %s:%s', cnt * BLOCK_SIZE, self.file.name, dst * BLOCK_SIZE)

  def do_write_block(self, src, dst, cnt):
    buff = []

    for _ in range(0, cnt * BLOCK_SIZE):
      buff.append(chr(self.machine.memory.read_u8(src)))
      src += 1

    buff = ''.join(buff)

    self.file.seek(dst * BLOCK_SIZE)
    self.file.write(buff)
    self.file.flush()

    debug('BIO: %s bytes written at %s:%s', cnt * BLOCK_SIZE, self.file.name, dst * BLOCK_SIZE)

#: List of known storage classes and their names.
STORAGES = {
  'block': FileBackedStorage,
}

class BlockIOInterrupt(VirtualInterrupt):
  """
  Virtual interrupt handler of block IO.
  """

  def run(self, core):
    """
    Execute requested IO operation. Arguments are passed in registers:

    - ``r0`` - device id
    - ``r1`` - ``0`` for read, ``1`` for write
    - ``r2`` - read: block id, write: src memory address
    - ``r3`` - read: dst memory address, write: block id
    - ``r4`` - number of blocks

    Current data segment is used for addressing memory locations.

    Success is indicated by ``0`` in ``r0``, any other value means error.
    """

    core.DEBUG('BIO requested')

    r0 = core.REG(Registers.R00)

    device = self.machine.get_storage_by_id(r0.value)
    if not device:
      core.WARN('BIO: unknown device: id=%s', r0.value)
      r0.value = 0xFFFF
      return

    r1 = core.REG(Registers.R01)
    r2 = core.REG(Registers.R02)
    r3 = core.REG(Registers.R03)
    r4 = core.REG(Registers.R04)
    DS = core.REG(Registers.DS)

    if r1.value == 0:
      handler = device.read_block
      src = r2.value
      dst = segment_addr_to_addr(DS.value & 0xFF, r3.value)

    elif r1.value == 1:
      handler = device.write_block
      src = segment_addr_to_addr(DS.value & 0xFF, r2.value)
      dst = r3.value

    else:
      core.WARN('BIO: unknown operation: op=%s', r1.value)
      r0.value = 0xFFFF
      return

    cnt = r4.value & 0x00FF

    try:
      r0.value = 0xFFFF
      handler(src, dst, cnt)
      r0.value = 0

    except StorageAccessError, e:
      core.ERROR('BIO: operation failed')
      core.EXCEPTION(e)

VIRTUAL_INTERRUPTS[InterruptList.BLOCKIO.value] = BlockIOInterrupt