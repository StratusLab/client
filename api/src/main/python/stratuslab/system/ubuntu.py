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
from BaseSystem import BaseSystem
from stratuslab.system.PackageInfo import PackageInfo
import stratuslab.Util as Util

installCmd = 'apt-get update && apt-get -y --force-yes install'
updateCmd = 'apt-get update'
cleanPackageCacheCmd = 'apt-get clean'
queryPackageCmd = 'dpkg -s'

class Ubuntu(BaseSystem):

    os = 'ubuntu'

    def __init__(self):
        self.systemName = 'Ubuntu 10.04'
        self.installCmd = installCmd
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

        self.packages = {'apache2': PackageInfo('apache2','/etc/apache2'),
                         'dhcp': PackageInfo('dhcp3-server',
                                             configFile='/etc/dhcp3/dhcpd.conf',
                                             initdScriptName='dhcp3-server'),
                        'MySQLServer': PackageInfo('mysql-server',
                                                   initdScriptName='mysql')}

        super(Ubuntu, self).__init__()

    # -------------------------------------------
    #     Package manager and related
    # -------------------------------------------

    def updatePackageManager(self):
        self._execute(['apt-get', 'update'])

    def getIsPackageInstalledCommand(self, package):
        cmd = "%s %s | grep Status | grep -q 'ok installed'" % (queryPackageCmd,
                                                                package)
        return cmd

    # -------------------------------------------
    #     Hypervisor related methods
    # -------------------------------------------

    def _configureKvm(self):
        super(Ubuntu, self)._configureKvm()
        self.executeCmd(['/etc/init.d/libvirt-bin start'])
        self.executeCmd(['usermod', '-G', 'libvirtd', '-a', self.oneUsername])

    # -------------------------------------------
    # Network related methods
    # -------------------------------------------

    FILE_INTERFACES = '/etc/network/interfaces'
    # re-defining for ubuntu
    FILE_FIREWALL_RULES = '/etc/iptables.rules'

    def _configureNetworkInterface(self, device, ip, netmask):
        data = """auto %s
iface %s inet static
  address %s
  netmask %s
  pre-up iptables-restore < %s""" % (device, device, ip, netmask,
                                     self.FILE_FIREWALL_RULES)

        Util.appendOrReplaceMultilineBlockInFile(self.FILE_INTERFACES, data)

    # -------------------------------------------
    # CA
    # -------------------------------------------

    def _installCAs(self):
        """CA:
        https://wiki.egi.eu/wiki/EGI_IGTF_Release
        http://repository.egi.eu/sw/production/cas/1/current/tgz/
        """
        Util.printDetail('NB! Installation of CA is not implemented for Ubuntu.')
        Util.printDetail("""For manual installation see:
        https://wiki.egi.eu/wiki/EGI_IGTF_Release
        http://repository.egi.eu/sw/production/cas/1/current/tgz/""")
        self._installFetchCrl()
        
    def _installFetchCrl(self):
        """fetch-crl 3:
        http://www.nikhef.nl/grid/fetchcrl3
        http://dist.eugridpma.info/distribution/util/fetch-crl3/
        """
        Util.printDetail('NB! Installation of fetch-crl is not implemented for Ubuntu.')
        Util.printDetail("""For manual installation see:
        http://www.nikhef.nl/grid/fetchcrl3
        http://dist.eugridpma.info/distribution/util/fetch-crl3/""")

system = Ubuntu()
