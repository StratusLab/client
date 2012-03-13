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

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printWarning
from stratuslab.AppRepo import AppRepo
from stratuslab.system import SystemFactory
from stratuslab.Util import getTemplateDir
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.installator.Claudia import Claudia
from stratuslab.installator.Monitoring import Monitoring
from stratuslab.installator.PersistentDisk import PersistentDisk
from stratuslab.installator.Registration import Registration
from stratuslab.installator.OpenLDAP import OpenLDAP
from stratuslab.installator.PolicyValidator import PolicyValidator
from stratuslab.installator.WebMonitor import WebMonitor
from stratuslab import Util
from stratuslab import Defaults

class BaseInstallator(object):

    def __init__(self):
        self.defaultStaticNetworks = ['public', 'local']
        self.defaultRangedNetworks = ['private']

        self.configHolder = None
        self.config = None
        self.options = {}
        self.nodeAddr = None
        self.appRepoAddr = None
        self.webMonitor = False
        self.installCloudia = None
        self.frontend = None
        self.node = None
        self.cloud = None
        self.onedTpl = os.path.join(getTemplateDir(), 'oned.conf.tpl')
        self.cloudVarLibDir = '/var/lib/one'
        self.registration = False
        self.openldap = False
        self.caching = False
        self.installRegistration = False
        self.installOpenLdap = False
        self.shareType = Defaults.SHARE_TYPE

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
            return
        elif self.appRepoAddr:
            printAction('Appliance Repository installation')
            self._runInstallAppRepo()
            printStep('Installation completed')
            return
        elif self.webMonitor:
            printAction('Web Monitor installation')
            self._runInstallWebMonitor()
            printStep('Installation completed')
            return
        elif self.installCloudia:
            printAction('Claudia installation')
            self._runInstallClaudia()
            return
        elif self.installMonitoring:
            printAction('Monitoring installation')
            self._runInstallMonitoring()
            return
        elif self.installOpenLdap:
            self._configureOpenLDAP()
            return
        elif self.installRegistration:
            self._configureRegistration()
            return
        
        # Front-end installation
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

        printStep('Configuring bridge')
        self._configureBridgeOnNode()

        printStep('Configuring file sharing')
        self._setupFileSharingClient()

        printStep('Adding node to cloud')
        self._addCloudNode()
        
        if self._isTrue(self.persistentDisk):
            self._runInstallNodePersistentDisk()

        if self.hypervisor == 'xen':
            print '\n\tPlease reboot the node on the Xen kernel to complete the installation'

    def _configureBridgeOnNode(self):
        self.node.configureBridgeRemotely()

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

    def _runInstallWebMonitor(self):
        webMonitor = WebMonitor(self.configHolder)
        webMonitor.run()

    def _runInstallClaudia(self):
        claudiaInstaller = Claudia(self.configHolder)
        claudiaInstaller.run()
        self._printInstalCompleted(claudiaInstaller.system.stdout.name, claudiaInstaller.system.stderr.name)
    def _runInstallMonitoring(self):
        monitoringInstaller = Monitoring(self.configHolder)
        monitoringInstaller.run()
        self._printInstalCompleted(monitoringInstaller.system.stdout.name, monitoringInstaller.system.stderr.name)
    def _runInstallFrontend(self):

        self._setCloud()

        self._setFrontend()
        printStep('Installing CAs')
        self._installCAs()

        printStep('Configuring file sharing')
        self._setupFileSharingServer()

        printStep('Configuring quarantine')
        self._configureQuarantine()

        printStep('Configuring cloud proxy service')
        self._configureCloudProxyService()

        printStep('Configuring firewall')
        self._configureFirewall()

        self._configureDhcpServer()

        printStep('Configuring database')
        self._configureDatabase()

        printStep('Configuring cloud admin account')
        self._configureCloudAdminFrontend()

        printStep('Configuring cloud system')
        self._configureCloudSystem()

        printStep('Applying local policies')
        self._configurePolicies()

        self._configureMarketPlacePolicyValidation()
        
        printStep('Starting cloud')
        self._startCloudSystem()

        printStep('Adding default ONE vnet')
        self._addDefaultNetworks()

        printStep('Adding default ACLs')
        self._addDefaultAcls()

        self._configureOpenLDAP()

        self._configureRegistration()

        self._runInstallFrontEndPersistentDisk()
        
    def _runInstallFrontEndPersistentDisk(self):
        if self._isTrue(self.persistentDisk):
            printAction('Storage installation')
            pdiskInstaller = PersistentDisk(self.configHolder)
            pdiskInstaller.runFrontend()
        
    def _runInstallNodePersistentDisk(self):
        printAction('Persistent disk storage installation')
        pdiskInstaller = PersistentDisk(self.configHolder)
        pdiskInstaller.runNode()
        
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
        self.node.configureCloudAdminSudoNode()
        self.node.configureCloudAdminPdiskNode()

    def _configureQuarantine(self):
        self.frontend.configureQuarantine()
        
    def _configureCloudProxyService(self):
        self.frontend.configureCloudProxyService()

    def _configureOpenLDAP(self):
        if self._isTrue(self.openldap):
            printAction('Configuring OpenLDAP')
            OpenLDAP(self.configHolder).run()

    def _configureRegistration(self):
        if self._isTrue(self.registration):
            printAction('Configuring Registration Service')
            Registration(self.configHolder).run()

    def _configureMarketPlacePolicyValidation(self):
        PolicyValidator(self.configHolder).run()

    def _isTrue(self, value):
        return Util.isTrueConfVal(value)

    def _configureFirewall(self):
        self.frontend.configureFirewall()

    def _configureDhcpServer(self):
        self.frontend.configureDhcpServer()

    def _configureDatabase(self):
        self.frontend.configureDatabase()

    def _configureCloudAdminFrontend(self):
        self.frontend.configureCloudAdminAccount()
        self.frontend.configureCloudAdminSshKeys()

    def _configureCloudSystem(self):
        pass

    def _configurePolicies(self):
        pass
    
    def _addDefaultNetworks(self):
        pass
    
    def _addDefaultAcls(self):
        pass

