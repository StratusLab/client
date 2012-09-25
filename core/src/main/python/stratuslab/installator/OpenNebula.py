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
from stratuslab.installator.Installator import Installator
from stratuslab.installator.PolicyValidator import PolicyValidator
from stratuslab.installator.OpenNebulaNode import OpenNebulaNode
from stratuslab.installator.OpenNebulaFrontend import OpenNebulaFrontend
from stratuslab.Util import printStep

class OpenNebula(OpenNebulaNode, OpenNebulaFrontend, Installator):
    
    def __init__(self, configHolder):
        super(OpenNebula, self).__init__(configHolder)

    def _installNode(self):
        printStep('Installing node dependencies')
        self._installNodeDependencies()
        self._warmXenNeedReboot()
        
    def _setupNode(self):
        printStep('Checking node connectivity')
        self._checkNodeConnectivity()

        printStep('Creating cloud admin account')
        self._createCloudAdmin(self.node)

        printStep('Configuring cloud admin account')
        self._configureCloudAdminNode()

        printStep('Configuring hypervisor')
        self._configureVirtualization()

        printStep('Configuring bridge')
        self._configureBridgeOnNode()

        printStep('Configuring file sharing')
        self._setupFileSharingClient()

        printStep('Adding node to cloud')
        self._assignDrivers()
        self._addCloudNode()
    
    def _installFrontend(self):
        printStep('Installing CAs')
        self._installCAs()
        
        printStep('Installing sendmail')
        self._installSendmail()
        
        self._printInstalCompleted(self.frontend.stdout.name, self.frontend.stderr.name)
        
    def _setupFrontend(self):
        printStep('Configuring file sharing')
        self._setupFileSharingServer()

        printStep('Configuring quarantine')
        self._configureQuarantine()

        printStep('Configuring cloud proxy service')
        self._configureCloudProxyService()

        printStep('Configuring firewall')
        self._configureFirewall()
        
        printStep('Configuring DHCP server')
        self._configureDhcpServer()

        printStep('Configuring database')
        self._configureDatabase()

        printStep('Configuring cloud admin account')
        self._configureCloudAdminFrontend()

        printStep('Configuring cloud system')
        self._configureCloudSystem()

        printStep('Applying local policies')
        self._configurePolicies()

        self._setupMarketPlacePolicyValidator()
        
        printStep('Starting cloud')
        self._startServicesFrontend()

        printStep('Adding default ONE vnet')
        self._addDefaultNetworks()

        printStep('Adding default ACLs')
        self._addDefaultAcls()

        self._printInstalCompleted(self.frontend.stdout.name, self.frontend.stderr.name)
        
    def _setupMarketPlacePolicyValidator(self):
        mpPolicyValidatorInstaller = PolicyValidator(self.configHolder)
        mpPolicyValidatorInstaller.setup()

    def _startServicesNode(self):
        printStep('Starting virtualization services')
        self._startVrtualization()

    def _printInstalCompleted(self, stdoutFilename, stderrFilename):
        printStep('Installation completed')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (stdoutFilename, stderrFilename)
