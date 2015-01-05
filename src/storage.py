import os
import stat
import threading

from io_handlers import IOHandler
from mm import ADDR_FMT, UINT8_FMT, UInt8, UInt16, UInt24, UInt32, segment_addr_to_addr
from util import debug

BLOCK_SIZE = 1024

class StorageAccessError(Exception):
  pass

class StorageIOHandler(IOHandler):
  def __init__(self, machine, *args, **kwargs):
    super(StorageIOHandler, self).__init__(*args, **kwargs)

    self.machine = machine

    self.lock = threading.Lock()

    self.op_index = 0
    self.op = None

  def read_u16_512(self):
    debug('read_u16_512')

    with self.lock:
      if self.op:
        debug('SIO running, defer caller')
        return UInt16(0)

      debug('reserve SIO')
      self.op = []
      self.op_index += 1
      return UInt16(self.op_index)

  def read_u16_514(self):
    debug('read_u16_514')

    with self.lock:
      if not self.op.is_set():
        debug('SIO still running')
        return UInt16(0)

      debug('SIO finished, reset')
      self.op = None
      return UInt16(self.op_index)

  def write_u16_514(self, value):
    self.op.append(value.u16)

    if len(self.op) != 7:
      return

    debug('start SIO: %s' % str(self.op))

    read = True if self.op[0] == 0 else False
    device = self.machine.get_storage_by_id(str(self.op[1]))
    if read:
      src = UInt32(self.op[2] | (self.op[3] << 16))
      dst = UInt24(segment_addr_to_addr(self.op[5] & 0xFF, self.op[4]))
    else:
      src = UInt24(segment_addr_to_addr(self.op[3] & 0xFF, self.op[2]))
      dst = UInt32(self.op[4] | (self.op[5] << 16))

    cnt = UInt8(self.op[6])

    target = device.read_block if read else device.write_block
    self.op = threading.Event()
    self.op.clear()

    debug('start SIO thread: target=%s, args=%s' % (target, str((src, dst, cnt, self.op))))
    sio_thread = threading.Thread(target = target, args = (src, dst, cnt, self.op))
    sio_thread.start()

class Storage(object):
  def __init__(self, machine, id, size):
    super(Storage, self).__init__()

    self.machine = machine
    self.id = id
    self.size = size

  def read_block(self, src, dst, cnt, event):
    debug('read_block: id=%s, src=%s, dst=%s, cnt=%s' % (self.id, src, dst, cnt))
    
    if src.u32 + cnt.u8 * BLOCK_SIZE >= self.size.u24:
      raise StorageAccessError('Out of bounds access: storage size %s is too small' % self.size)

    self.do_read_block(src, dst, cnt)

    event.set()

  def write_block(self, src, dst, cnt, event):
    debug('write_block: id=%s, src=%s, dst=%s, cnt=%s' % (self.id, src, dst, cnt))

    if dst.u32 + BLOCK_SIZE * cnt.u8 >= self.size.u32:
      raise StorageAccessError('Out of bounds access: storage size %s is too small' % self.size)

    self.do_write_block(src, dst, cnt)

    event.set()

class FileBackedStorage(Storage):
  def __init__(self, machine, id, path):
    st = os.stat(path)

    super(FileBackedStorage, self).__init__(machine, id, UInt24(st.st_size))

    self.lock = threading.Lock()
    self.path = path
    self.file = None

  def boot(self):
    self.file = open(self.path, 'r+b')

  def halt(self):
    self.file.close()

  def do_read_block(self, src, dst, cnt):
    debug('do_read_block: src=%s, dst=%s, cnt=%s' % (src, dst, cnt))

    with self.lock:
      self.file.seek(src.u32)
      buff = self.file.read(BLOCK_SIZE * cnt.u8)

    u = UInt8()
    for c in buff:
      u.u8 = ord(c)
      self.machine.memory.write_u8(dst.u24, u.u8)
      dst.u24 += 1

  def do_write_block(self, src, dst, cnt):
    buff = []

    for _ in range(0, BLOCK_SIZE * cnt.u8):
      buff.append(chr(self.machine.memory.read_u8(src.u24).u8))
      src.u24 += 1

    buff = ''.join(buff)

    with self.lock:
      self.file.seek(dst.u32)
      self.file.write(buff)

STORAGES = {
  'block': FileBackedStorage,
}
