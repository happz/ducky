import logging
import os.path
import subprocess

import ducky.snapshot

from testconfig import config
from functools import partial
from six import iteritems

tests_dir = partial(os.path.join, config['dirs']['tests'])
forth_dir = partial(os.path.join, config['dirs']['forth'])
logs_dir  = partial(os.path.join, config['dirs']['logs'], 'examples')
examples_dir = partial(os.path.join, config['dirs']['examples'])
loader_dir   = partial(os.path.join, config['dirs']['loader'])
snapshots_dir = partial(os.path.join, config['dirs']['snapshot'])

def run_example(name, binary_name = None, options = None, exit_code = 0, snapshot_device = None):
  binary_name = binary_name or name
  options = options or []

  cmd = [
    config['vm-runner']['ducky-vm'],
    '--machine-config=%s' % examples_dir(name, '%s.conf' % binary_name),
    '--set-option=bootloader:file=%s' % examples_dir(name, binary_name),
  ]

  if snapshot_device is not None:
    cmd += [
      '--set-option=%s:driver=ducky.devices.snapshot.FileSnapshotStorage' % snapshot_device,
      '--set-option=%s:filepath=%s' % (snapshot_device, snapshots_dir(name))
    ]

  cmd += options

  env = os.environ.copy()

  if 'COVERAGE_FILE' in os.environ:
    cmd[0] = '%s %s' % (config['vm-runner']['coverage'], cmd[0])
    env['COVERAGE_FILE'] = os.path.join(config['dirs']['coverage'], '.coverage.example.%s' % name)

  cmd[0] = '%s %s' % (config['vm-runner']['runner'], cmd[0])

  machine_log = logs_dir('example-%s.machine' % name)

  with open(config['log']['trace'], 'a') as f_trace:
    f_trace.write('CMD: %s\n' % ' '.join(cmd))
    f_trace.write('ENV:\n')
    for k, v in iteritems(env):
      f_trace.write('   %s=%s\n' % (k, v))

  logging.getLogger().info(' '.join(cmd))

  with open(machine_log, 'w') as f_out:
    with open('/dev/null', 'r') as f_in:
      try:
        subprocess.check_call(' '.join(cmd), stdout = f_out, stderr = f_out, stdin = f_in, shell = True, env = env)

      except subprocess.CalledProcessError as e:
        if e.returncode != exit_code:
          assert False, 'Example VM failed with exit code %s' % e.returncode

      else:
        if exit_code != 0:
          assert False, 'Example VM failed with exit code %s' % e.returncode

def test_exceptions():
  run_example('exceptions')

def test_hello_world():
  run_example('hello-world')

def test_hello_world_lib():
  run_example('hello-world-lib', binary_name = 'hello-world')

def test_clock():
  run_example('clock')

def test_fib():
  run_example('fib', snapshot_device = 'device-3')

  with ducky.snapshot.CoreDumpFile.open(logging.getLogger(), snapshots_dir('fib'), 'r') as f_in:
    state = f_in.load()

    assert state.get_child('machine').get_cpu_states()[0].get_core_states()[0].registers[0] == 0x000CB228

def test_simple_loop():
  run_example('simple-loop')

def test_svga():
  run_example('vga')

def test_smp():
  run_example('smp', options = ['--set-option=bootloader:file=%s' % loader_dir('loader'), '--set-option=device-6:filepath=%s' % examples_dir('smp', 'smp.img')], exit_code = 1, snapshot_device = 'device-4')

  expected_exit_codes = [
    [0x00000000, 0x00000001],
    [0x00010000, 0x00010001]
  ]

  with ducky.snapshot.CoreDumpFile.open(logging.getLogger(), snapshots_dir('smp'), 'r') as f_in:
    state = f_in.load()

    for cpu_state in state.get_child('machine').get_cpu_states():
      for core_state in cpu_state.get_core_states():
        expected_exit_code = expected_exit_codes[core_state.cpuid][core_state.coreid]

        assert expected_exit_code == core_state.exit_code, 'Core #%d:#%d has unexpected exit code: 0x%08X instead of 0x%08X' % (core_state.cpuid, core_state.coreid, core_state.exit_code, expected_exit_code)
