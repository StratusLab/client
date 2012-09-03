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
from stratuslab.installator.OpenNebulaCommon import OpenNebulaCommon
from stratuslab.system import SystemFactory
from stratuslab.Exceptions import OneException
from stratuslab.Util import printWarning, printError

class OpenNebulaNode(OpenNebulaCommon):
    
    def __init__(self, configHolder):
        self.node = None

        super(OpenNebulaNode, self).__init__(configHolder)

        self._setNodeSystem()

    def _setNodeSystem(self):
        if self.nodeAddr:
            self.node = SystemFactory.getSystem(self.nodeSystem, self.configHolder)
            self.node.workOnNode()
        
    def _warmXenNeedReboot(self):
        if self.hypervisor == 'xen':
            print '\n\tPlease reboot the node on the Xen kernel to complete the installation'
            
    def _nodeAlive(self):
        return self.node._nodeShell('exit 42') == 42
    
    def _checkNodeConnectivity(self):
        if not self._nodeAlive():
            printError('Unable to connect the node %s' % self.nodeAddr)
    
    def _configureCloudAdminNode(self):
        self.node.configureCloudAdminSshKeysNode()
        self.node.configureCloudAdminSudoNode()
        self.node.configureCloudAdminPdiskNode()
    
    def _addCloudNode(self):
        # This just assumes that a node can't be added because it exists
        # already.  A better implementation would check to see if it 
        # really does exists and if so, returns the existing node id.
        try:
            return self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver)
        except OneException:
            printWarning('Couldn\'t add host, already present?')
            # The id is actually ignored, so this should be ok.
            return -1
        
    def _installNodeDependencies(self):
        self.node.installNodeDependencies()
        self.node.installHypervisor()
        self.node.configureHypervisor()
        
    def _configureBridgeOnNode(self):
        self.node.configureBridgeRemotely()
        
    def _setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(self.shareType, []))
        self._configureFileSharingClient()

    def _configureFileSharingClient(self):
        if self.shareType == 'nfs':
            self._configureNfsClient()
        elif self.shareType in ('ssh', 'stratuslab'):
            self.node.configureSshClient(self.cloudVarLibDir)
        else:
            printError('Unable to determine node share type. Got %s' % self.shareType)
         
    def _configureNfsClient(self):
        mountPoint = self.cloudVarLibDir
        if self._nfsShareAlreadyExists():
            host = self.config.get('existing_nfs')
        else:
            host = '%s:%s' % (self.config['frontend_ip'], self.cloudVarLibDir)
        self.node.configureExistingNfsShare(host, mountPoint)
        