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
import os

from BaseInstallator import BaseInstallator
from stratuslab.Util import fileGetContent
import stratuslab.Util as Util

class OneInstallator(BaseInstallator):
    
    def __init__(self):
        super(OneInstallator, self).__init__()
        self.cloudConfDir = '/etc/one/'
        self.cloudConfFile = self.cloudConfDir + 'oned.conf'

    def _addCloudNode(self):
        return self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver)
        
    def _removeCloudNode(self, id):
        self.cloud.hostRemove(id)
        
    def _addDefaultNetworks(self):
        for vnet in self.defaultStaticNetworks:
            self.cloud.networkCreate(self._buildFixedNetworkTemplate(vnet))
        for vnet in self.defaultRangedNetworks:
            self.cloud.networkCreate(self._buildRangedNetworkTemplate(vnet))

    def _buildFixedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(Util.shareDir + 'vnet/fixed.net')
        
        ipMacs = zip(self.config.get('one_%s_network_addr' % networkName).split(' '),\
                     self.config.get('one_%s_network_mac' % networkName).split(' '))
        leases = ['LEASES = [ IP="%s", MAC="%s"]' % (ip, mac) for ip, mac in ipMacs]

        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'leases': '\n'.join(leases)})
        return vnetTpl

    def _buildRangedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(Util.shareDir + 'vnet/ranged.net')
        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'network_size': self.config.get('one_%s_network_size' % networkName),
                             'network_addr': self.config.get('one_%s_network' % networkName)})
        return vnetTpl

    # -------------------------------------------
    #   Front-end file sharing management
    # -------------------------------------------
    
    def _setupFileSharingServer(self):
        self.frontend.installPackages(self.frontend.fileSharingFrontendDeps.get(self.shareType, []))
        self._configureFileSharingServer()

    def _configureFileSharingServer(self):
        if self.shareType == 'nfs':
            self._configureNfsServer()
        elif self.shareType == 'ssh':
            self.frontend.configureSshServer()

    # ---- NFS configuration

    def _configureNfsServer(self):
        if self._nfsShareAlreadyExists():
            if self.config.get('vm_dir') != '':
                mountPoint = self.config.get('vm_dir')
            else:
                mountPoint = os.path.dirname(self.config.get('one_home'))

            self.frontend.configureExistingNfsShare(self.config.get('existing_nfs'), mountPoint)
        else:
            if self.config.get('vm_dir') != '':
                mountPoint = self.config.get('vm_dir')
            else:
                mountPoint = '%s/var' % self.config.get('one_home')

            self.frontend.configureNewNfsServer(mountPoint,
                                                self.config['network_addr'],
                                                self.config['network_mask'])

    def _nfsShareAlreadyExists(self):
        return not (self.config.get('existing_nfs', '') == '')
    
    # -------------------------------------------
    #    Node file sharing management
    # -------------------------------------------

    def _setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(self.shareType, []))
        self._configureFileSharingClient()

    def _configureFileSharingClient(self):
        if self.shareType == 'nfs':
            self._configureNfsClient()
        elif self.shareType == 'ssh':
            self.node.configureSshClient(self.config.get('vm_dir'))
    
    # ---- NFS configuration   
         
    def _configureNfsClient(self):
        if self._nfsShareAlreadyExists():
            if self.config.get('vm_dir') != '':
                host = self.config.get('existing_nfs')
                mountPoint = self.config.get('vm_dir')
            else:
                host = '%s/%s/var' % (self.config.get('existing_nfs'),
                                  os.path.basename(self.config.get('one_home')))
                mountPoint = '%s/var' % self.config.get('one_home')
        else:
            if self.config.get('vm_dir') != '':
                host = '%s:%s' % (self.config['frontend_ip'], self.config.get('vm_dir'))
                mountPoint = self.config.get('vm_dir')
            else:
                host = '%s:%s/var' % (self.config['frontend_ip'], self.config.get('one_home'))
                mountPoint = '%s/var' % self.config.get('one_home')

        self.node.configureExistingNfsShare(host, mountPoint)
