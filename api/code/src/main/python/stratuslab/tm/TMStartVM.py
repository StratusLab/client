#!/usr/bin/env python
#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import libvirt
import stat
from uuid import UUID

class TMStartVM(object):
    ''' 
    Creates a VM machine description and then launches the machine
    using the libvirt API.
    '''

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSELEVEL = 0

    # Machine template.
    vm_tpl = """<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
  <uuid>%(uuid)s</uuid>
  <name>%(name)s</name>
  <vcpu>%(vcpu)d</vcpu>
  <memory>%(ram)d</memory>

  <os>
    <type arch='%(cpuArch)s'>hvm</type>
    <boot dev='hd'/>
  </os>

  <devices>
    <emulator>/usr/bin/qemu-kvm</emulator>

%(disks)s

%(context)s

    <interface type='bridge'>
      <source bridge='br0'/>
      <mac address='%(mac)s'/>
    </interface>

    <graphics type='vnc' port='-1'/>
  </devices>

  <features>
    <acpi/>
  </features>
</domain>
"""

    disk_tpl = """
    <disk type='file' device='disk'>
      <source file='%(file)s'/>
      <target dev='%(target)s'/>
      <driver name='qemu' type='raw' cache='default'/>
    </disk>
"""

    context_tpl = """
    <disk type='file' device='cdrom'>
      <source file='%(context)s'/>
      <target dev='hdd'/>
      <readonly/>
      <driver name='qemu' type='raw'/>
    </disk>
"""

    def __init__(self, args, **kwargs):
        self.args = args

        libvirt_url = 'qemu:///system'
        self.connection = libvirt.open(libvirt_url)

    def run(self):
        try:
            self._run()
        finally:
            self._cleanup()

    def _run(self):

        TMStartVM._checkArgs(self.args)

        opts = {}
        opts['uuid'] = uuid.uuid1().hex
        opts['name'] = 'StratusLab'
        opts['vcpu'] = 2
        opts['cpuArch'] = 'x86_64'
        opts['ram'] = 1024 * 1024 * 1024 # 1 GiB
        opts['mac'] = '0a:0a:86:9e:49:33'

        opts['disks'] = ''

        opts['context'] = ''

        descriptor = vm_tpl % opts

        print descriptor

        dom = self.connection.createLinux(descriptor, 0)
        if dom == None:
            print "failed"
        else:
            print "done"

    def _cleanup(self):
        pass

    @staticmethod
    def _checkArgs(args):
        pass

