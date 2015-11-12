import random
import string
import os

import ducky.devices.storage

from ducky.mm import segment_addr_to_addr
from .. import common_run_machine, prepare_file, common_asserts, TestCase
from functools import partial

def common_case(mm_asserts = None, file_asserts = None, **kwargs):
  common_run_machine(post_run = [partial(common_asserts, mm_asserts = mm_asserts, file_asserts = file_asserts, **kwargs)], **kwargs)

class Tests(TestCase):
  def test_unknown_device(self):
    f_tmp = prepare_file(ducky.devices.storage.BLOCK_SIZE * 10)

    common_case(binary = os.path.join(os.getenv('CURDIR'), 'tests', 'storage', 'test_unknown_device_1.testbin'),
                storages = [('ducky.devices.storage.FileBackedStorage', 1, f_tmp.name)],
                r0 = 0xFFFF, z = 1)

  def test_out_of_bounds_access(self):
    data_base = 0x1000 if os.getenv('MMAPABLE_SECTIONS')  == 'yes' else 0x0100

    f_tmp = prepare_file(ducky.devices.storage.BLOCK_SIZE * 10)

    common_case(binary = os.path.join(os.getenv('CURDIR'), 'tests', 'storage', 'test_out_of_bounds_access_read.testbin'),
                storages = [('ducky.devices.storage.FileBackedStorage', 1, f_tmp.name)],
                r0 = 0xFFFF, r2 = 16, r3 = data_base, r4 = 1)
    common_case(binary = os.path.join(os.getenv('CURDIR'), 'tests', 'storage', 'test_out_of_bounds_access_write.testbin'),
                storages = [('ducky.devices.storage.FileBackedStorage', 1, f_tmp.name)],
                r0 = 0xFFFF, r1 = 1, r2 = 16, r3 = data_base, r4 = 1)

  def test_block_read(self):
    # size of storage file
    file_size   = ducky.devices.storage.BLOCK_SIZE * 10
    # message length
    msg_length  = 64
    # msg resides in this block
    msg_block  = random.randint(0, (file_size / ducky.devices.storage.BLOCK_SIZE) - 1)

    # create random message
    msg = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(msg_length))

    f_tmp = prepare_file(file_size, messages = [(msg_block * ducky.devices.storage.BLOCK_SIZE, msg)])

    storage_desc = ('ducky.devices.storage.FileBackedStorage', 1, f_tmp.name)

    data_base = 0x1000 if os.getenv('MMAPABLE_SECTIONS') == 'yes' else 0x0100
    ph_data_base = segment_addr_to_addr(2, data_base)

    # prepare mm assert dict, and insert message and redzones in front and after the buffer
    mm_assert = [
      (ph_data_base, msg_block),
      (ph_data_base + 2, 0xFEFE),
      (ph_data_base + 4 + ducky.devices.storage.BLOCK_SIZE, 0xBFBF)
    ]

    file_assert = [
      (f_tmp.name, {})
    ]

    for i in range(0, msg_length, 2):
      mm_assert.append((ph_data_base + 4 + i, ord(msg[i]) | (ord(msg[i + 1]) << 8)))
      file_assert[0][1][msg_block * ducky.devices.storage.BLOCK_SIZE + i] = ord(msg[i])
      file_assert[0][1][msg_block * ducky.devices.storage.BLOCK_SIZE + i + 1] = ord(msg[i + 1])

    common_case(binary = os.path.join(os.getenv('CURDIR'), 'tests', 'storage', 'test_block_read.testbin'),
                storages = [storage_desc], pokes = [(ph_data_base, msg_block, 2)],
                mm_asserts = mm_assert, file_asserts = file_assert,
                r0 = 0, r1 = 0, r2 = msg_block, r3 = data_base + 4, r4 = 1)

  def test_block_write(self):
    # size of file
    file_size   = ducky.devices.storage.BLOCK_SIZE * 10
    # message length
    msg_length  = 64
    # msg resides in this offset
    msg_block  = random.randint(0, (file_size / ducky.devices.storage.BLOCK_SIZE) - 1)

    # create random message
    msg = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(msg_length))
    msg += (chr(0x61) * (ducky.devices.storage.BLOCK_SIZE - msg_length))

    # create file that we later mmap, filled with pseudodata
    f_tmp = prepare_file(file_size)

    storage_desc = ('ducky.devices.storage.FileBackedStorage', 1, f_tmp.name)

    data_base = 0x1000 if os.getenv('MMAPABLE_SECTIONS') == 'yes' else 0x0100
    ph_data_base = segment_addr_to_addr(2, data_base)

    mm_assert = []

    file_assert = [
      (f_tmp.name, {})
    ]

    for i in range(0, ducky.devices.storage.BLOCK_SIZE, 2):
      mm_assert.append((ph_data_base + 2 + i, ord(msg[i]) | (ord(msg[i + 1]) << 8)))
      file_assert[0][1][msg_block * ducky.devices.storage.BLOCK_SIZE + i] = ord(msg[i])
      file_assert[0][1][msg_block * ducky.devices.storage.BLOCK_SIZE + i + 1] = ord(msg[i + 1])

    common_case(binary = os.path.join(os.getenv('CURDIR'), 'tests', 'storage', 'test_block_write.testbin'),
                storages = [storage_desc], pokes = [(ph_data_base, msg_block, 2)] + [(ph_data_base + 2 + i, ord(msg[i]), 1) for i in range(0, ducky.devices.storage.BLOCK_SIZE)],
                mm_asserts = mm_assert, file_assertss = file_assert,
                r0 = 0, r1 = 1, r2 = data_base + 2, r3 = msg_block, r4 = 1)
