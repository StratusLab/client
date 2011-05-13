#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
from stratuslab.system.centos import CentOS
from stratuslab.system.PackageInfo import PackageInfo
from stratuslab import Util

class Fedora(CentOS):
    def __init__(self):
        super(Fedora, self).__init__()
        self.frontendDeps = [
                'openssh', 'ruby', 'zlib-devel', 'curl'
        ]
        
        self.packages['dhcp'] = PackageInfo('dhcp',
                                            configFile='/etc/dhcp/dhcpd.conf',
                                            initdScriptName='dhcpd')
        
    def _configureKvm(self):
        self.executeCmd(['modprobe', 'kvm_intel'])
        self.executeCmd(['modprobe', 'kvm_amd'])
        
        self.executeCmd('/etc/init.d/libvirtd stop'.split())

        libvirtConf = '/etc/libvirt/libvirtd.conf'
        self.appendOrReplaceInFileCmd(libvirtConf, '^unix_sock_group.*$',
                                      'unix_sock_group = "cloud"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^unix_sock_ro_perms.*$',
                                      'unix_sock_ro_perms = "0777"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^unix_sock_rw_perms.*$',
                                      'unix_sock_rw_perms = "0770"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^auth_unix_ro.*$',
                                      'auth_unix_ro = "none"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^auth_unix_rw.*$',
                                      'auth_unix_rw = "none"')

        qemuConf = '/etc/libvirt/qemu.conf'
        self.appendOrReplaceInFileCmd(qemuConf, '^vnc_listen.*$',
                                      'vnc_listen = "0.0.0.0"')

        self.executeCmd('ln -s /usr/bin/qemu-kvm /usr/libexec/qemu-kvm'.split())
        self.executeCmd('ln -s /usr/bin/qemu-kvm /usr/bin/kvm'.split())
        
        rc, output = self.executeCmd('/etc/init.d/libvirtd start'.split(), withOutput=True)
        if rc != 0:
            Util.printError('Could not start libvirt.\n%s' % output)


system = Fedora()
