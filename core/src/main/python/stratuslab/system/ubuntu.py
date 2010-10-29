#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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
from BaseSystem import BaseSystem
from stratuslab.Util import fileGetContent
from stratuslab.system.PackageInfo import PackageInfo
import stratuslab.Util as Util

class Ubuntu(BaseSystem):

    def __init__(self):
        self.systemName = 'Ubuntu 10.04'
        self.installCmd = 'apt-get -q -y install' 
        self.frontendDeps = [
            'ruby', 'libsqlite3-dev', 'libxmlrpc-c3-dev', 'libssl-dev',
            'scons', 'g++', 'git-core', 'ssh', 'genisoimage', 'curl', 'libxml2-dev'
        ]
        self.nodeDeps = ['ssh', 'ruby', 'curl', 'libvirt-bin', 'genisoimage' ]
        self.hypervisorDeps = {
            'xen': ['xen-hypervisor-3.3'],
            'kvm': ['qemu-kvm'],
        }
        self.fileSharingFrontendDeps = {
            'nfs': ['nfs-kernel-server'],
            'ssh': [],
        }
        self.fileSharingNodeDeps = {
            'nfs': ['nfs-common'],
            'ssh': [],
        }
        
        self.packages = {'apache2': PackageInfo('apache2','/etc/apache2')}

        super(Ubuntu, self).__init__()

    # -------------------------------------------
    #     Package manager and related
    # -------------------------------------------

    def updatePackageManager(self):
        self._execute(['apt-get', 'update'])

    def installPackages(self, packages):
        if len(packages) < 1:
            return

        cmd = self.installCmd.split(' ')
        cmd.extend(packages)
        self._execute(cmd)

    def installNodePackages(self, packages):
        if len(packages) > 0:
            self._nodeShell('%s %s' % 
                (self.installCmd, ' '.join(packages)))
            
    # -------------------------------------------
    #     Hypervisor related methods
    # -------------------------------------------
            
    def _configureKvm(self):
        super(Ubuntu, self)._configureKvm()
        self.executeCmd(['/etc/init.d/libvirt-bin start'])
        self.executeCmd(['usermod', '-G', 'libvirtd', '-a', self.oneUsername])
        
    # -------------------------------------------
    #     Network configuration and related
    # -------------------------------------------
        
    def configureNetwork(self, networkInterface, bridge):
        for iface in (networkInterface, bridge):
            self.executeCmd(['sed -i \'s/.*%s.*/#&/\' /etc/network/interfaces' % iface])
        
        self.fileAppendContentsCmd('/etc/network/interfaces',
                fileGetContent(Util.shareDir + 'template/debian.br.tpl') % ({'bridge': bridge, 'iface': networkInterface}))

        self.executeCmd(['/etc/init.d/networking restart'])

system = Ubuntu()

