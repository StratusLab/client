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
import os

from stratuslab.Util import fileGetContent
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printWarning
from stratuslab.Util import shareDir
from stratuslab.AppRepo import AppRepo
from stratuslab.system import SystemFactory
from stratuslab.Util import printError
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.installator.Claudia import Claudia

class BaseInstallator(object):

    def __init__(self):
        self.defaultStaticNetworks = ['public', 'local']
        self.defaultRangedNetworks = ['private']

        self.configHolder = None
        self.config = None
        self.options = {}
        self.nodeAddr = None
        self.appRepoAddr = None
        self.installCloudia = None
        self.frontend = None
        self.node = None
        self.cloud = None
        self.onedTpl = shareDir + 'template/oned.conf.tpl'
        self.cloudVarLibDir = '/var/lib/one'

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
        elif self.installCloudia:
            printAction('Claudia installation')
            self._runInstallClaudia()
            return
        else:
            printAction('Frontend installation')
            self._runInstallFrontend()
            self._printInstalCompleted(self.frontend.stdout.name, self.frontend.stderr.name)


    def _printInstalCompleted(self, stdoutFilename, stderrFilename):
        printStep('Installation completed')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (stdoutFilename, stderrFilename)

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
        self.username = self.oneUsername
        self.password = self.onePassword
        credentials = LocalhostCredentialsConnector(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.configHolder.assign(self.cloud)
        self.cloud.setEndpoint('localhost')

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

    def _runInstallClaudia(self):
        claudiaInstaller = Claudia(self.configHolder)
        claudiaInstaller.run()
        self._printInstalCompleted(claudiaInstaller.system.stdout.name, claudiaInstaller.system.stderr.name)

    def _runInstallFrontend(self):

        self._setCloud()

        self._setFrontend()

        printStep('Installing CAs')
        self._installCAs()

        printStep('Configuring file sharing')
        self._setupFileSharingServer()

        printStep('Configuring cloud proxy service')
        self._configureCloudProxyService()

        printStep('Configuring firewall')
        self._configureFireWall()

        self._configureDhcpServer()

        printStep('Configuring database')
        self._configureDatabase()

        printStep('Configuring cloud admin account')
        self._configureCloudAdminFrontend()

        printStep('Configuring cloud system')
        self._configureCloudSystem()

        printStep('Applying local policies')
        self._configurePolicies()

        printStep('Starting cloud')
        self._startCloudSystem()

        printStep('Adding default ONE vnet')
        self._addDefaultNetworks()

    def _installCAs(self):
        self.frontend.installCAs()

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
        self.node.configureCloudAdminSshKeysNode()

    def _configureCloudProxyService(self):
        self.frontend.configureCloudProxyService()

    def _configureFireWall(self):
        self.frontend.configureFireWall()

    def _configureDhcpServer(self):
        self.frontend.configureDhcpServer()

    def _configureDatabase(self):
        self.frontend.configureDatabase()

    def _configureCloudAdminFrontend(self):
        self.frontend.configureCloudAdminAccount()
        self.frontend.configureCloudAdminSshKeys()

    def _configureCloudSystem(self):
        if not os.path.isfile(self.onedTpl):
            printError('ONe daemon configuration template '
                       '%s does not exists' % self.onedTpl)

        conf = self.config.copy()
        conf['vm_dir'] = self.cloudVarLibDir
        self.frontend.filePutContentsCmd(self.cloudConfFile,
                                         fileGetContent(self.onedTpl) % conf)

    def _configurePolicies(self):
        pass

    def _addDefaultNetworks(self):
        pass

    def _assignKey(self, options, config):
        self.privateKey = (True and options.privateKey) or (self.nodePrivateKey)

