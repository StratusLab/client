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

from stratuslab.Util import fileGetContent
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printWarning
from stratuslab.AppRepo import AppRepo
from stratuslab.system import SystemFactory
from stratuslab.Util import printError


class BaseInstallator(object):
    
    def __init__(self):
        # Default network added automatically at installation
        # Make sure one_%(name)s_* exist in the config 
        self.defaultNetworks = ['private', 'public']
        
        self.configHolder = None
        self.config = None
        self.options = {}
        self.nodeAddr = None
        self.frontend = None
        self.node = None
        self.stdout = None
        self.stderr = None
        self.cloud = None

    def runInstall(self, configHolder):
        # TODO: fix the logs for apprepo installs
        self.configHolder = configHolder
        configHolder.assign(self)

        self._assignDrivers()

        self.options = configHolder.options
        self.config = configHolder.config
        
        if self.nodeAddr:
            printAction('Node(s) installation')
            self._runInstallNodes()
        elif self.appRepoAddr:
            printAction('Appliance Repository installation')
            self._runInstallAppRepo()
            printStep('Installation completed')
            return
        else:
            printAction('Frontend installation')
            self._runInstallFrontend()
            
        printStep('Installation completed')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (self.frontend.stdout.name, 
                                                                        self.frontend.stderr.name)

    def _assignDrivers(self):
        self.infoDriver = (True and self.infoDriver) or ('im_%s' % self.hypervisor)
        self.virtDriver = (True and self.virtDriver) or ('vmm_%s' % self.hypervisor)
        self.transfertDriver = (True and self.transfertDriver) or ('tm_%s' % self.shareType)
          
    def _runInstallNodes(self):

        self._setFrontend()

        self._setCloud()

        self.node = SystemFactory.getSystem(self.nodeSystem, self.configHolder)

        #TODO: reduce amount of data having to be manually propagated
        self._propagateNodeInfos()

        printStep('Checking node connectivity')
        if not self._nodeAlive():
            raise ValueError('Unable to connect the node %s' % self.nodeAddr)

        printStep('Creating cloud admin account')
        self._createCloudAdmin(self.node)
        
        printStep('Configuring cloud admin account')
        self._configureCloudAdminNode()
        
        printStep('Installing dependencies')
        self._installNodeDependencies()
        
        printStep('Configuring file sharing')
        self._setupFileSharingClient()
        
        printStep('Adding node to cloud')
        self._addCloudNode()
        
        if self.hypervisor == 'xen':
            print '\n\tPlease reboot the node on the Xen kernel to complete the installation'

    def _setCloud(self):
        self.cloud = CloudConnectorFactory.getCloud()
        self.configHolder.assign(self.cloud)
        
        self.cloud.setEndpointFromParts(self.frontendIp, self.onePort)
        self.cloud.setCredentials(self.oneUsername, self.onePassword)

    def _propagateNodeInfos(self):
        self.node.setNodeAddr(self.nodeAddr)
        self.node.setNodePrivateKey(self.privateKey)
        self.node.setNodePort(self.nodeSshPort)
        self.node.setNodeHypervisor(self.hypervisor)
        self.node.workOnNode()
        self.frontend.setCloudAdminName(self.oneUsername)
        
    def _runInstallAppRepo(self):
        appRepo = AppRepo(self.configHolder)
        appRepo.run()

    def _runInstallFrontend(self):
        printStep('Configuring file sharing')

        self._setCloud()

        self._setFrontend()

        self._setupFileSharingServer()

        printStep('Configuring cloud admin account')
        self._configureCloudAdminFrontend()
        
        printStep('Configuring cloud system')
        self._configureCloudSystem()
        
        printStep('Starting cloud')
        self._startCloudSystem()

        printStep('Adding default ONE vnet')
        self._addDefaultNetworks()
        
    def _setFrontend(self):
        if not self.frontendIp or self.frontendIp == '127.0.0.1':
            printWarning('frontend_ip configuration parameter is %s, this is very likely not to work' % self.frontendIp)
        self.frontend = SystemFactory.getSystem(self.frontendSystem, self.configHolder)

    def _nodeAlive(self):
        return self.node._nodeShell('exit 42') == 42
    
    def _startCloudSystem(self):
        self.frontend.startCloudSystem()

    def _installNodeDependencies(self):
        self.node.installNodeDependencies()
        self.node.installHypervisor()
        self.node.configureHypervisor()

    def _createCloudAdmin(self, system):
        system.createCloudGroup(self.oneGroup,
                                self.oneGid)
        system.createCloudAdmin()

    def _installCloudSystem(self):
        pass
    
    def _setupFileSharingClient(self):
        pass
    
    def _addCloudNode(self):
        pass
    
    def _configureCloudAdminNode(self):
#        self.configureNodeNetwork()
        self.node.configureCloudAdminSshKeysNode()
        self._copyCloudHooks(self.node)

    def _configureCloudAdminFrontend(self):
#        self.frontend.configureCloudAdminEnv(self.config.get('one_port'),
#                                             self.config.get('stratuslab_location'))
        self.frontend.configureCloudAdminAccount()
        self.frontend.configureCloudAdminSshKeys()
        self._copyCloudHooks(self.frontend)

        if self.vmDir != '':
            self.frontend.createDirsCmd(self.vmDir)
            self.frontend.setOwnerCmd(self.vmDir)
        
    def _configureCloudSystem(self):
        if not os.path.isfile(self.onedTpl):
            printError('ONe daemon configuration template '
                       '%s does not exists' % self.onedTpl)

        conf = self.config.copy()
        self.frontend.filePutContentsCmd(self.cloudConfFile,
                                         fileGetContent(self.onedTpl) % conf)

    def _addDefaultNetworks(self):
        pass

    def _assignKey(self, options, config):
        self.privateKey = (True and options.privateKey) or (self.nodePrivateKey)
