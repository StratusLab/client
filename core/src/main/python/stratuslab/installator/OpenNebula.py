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
import stratuslab.Util as Util

from stratuslab.Util import fileGetContent, printStep, getTemplateDir,\
    printWarning
from stratuslab.Exceptions import OneException
from stratuslab import Defaults
from stratuslab.system import SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.installator.PolicyValidator import PolicyValidator
from stratuslab.installator.Registration import Registration

class OpenNebula(Installator):
    
    def __init__(self, configHolder):
        self.defaultStaticNetworks = ['public', 'local']
        self.defaultRangedNetworks = ['private']

        self.configHolder = configHolder
        configHolder.assign(self)

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
        self.caching = False
        self.shareType = Defaults.SHARE_TYPE
        self.cloudConfDir = Defaults.CLOUD_CONF_DIR
        self.cloudConfFile = Defaults.CLOUD_CONF_FILE
        
    def _installNode(self):
        printStep('Installing node dependencies')
        self._installNodeDependencies()
        if self.hypervisor == 'xen':
            print '\n\tPlease reboot the node on the Xen kernel to complete the installation'
        
    def _setupNode(self):
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

        printStep('Configuring bridge')
        self._configureBridgeOnNode()

        printStep('Configuring file sharing')
        self._setupFileSharingClient()

        printStep('Adding node to cloud')
        self._addCloudNode()
    
    def _installFrontend(self):
        self._setCloud()

        self._setFrontend()
        printStep('Installing CAs')
        self._installCAs()
        
        self._printInstalCompleted(self.frontend.stdout.name, self.frontend.stderr.name)
        
    def _setupFrontend(self):
        self._setCloud()

        self._setFrontend()

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

        self._configureRegistrationApplication()
        self._printInstalCompleted(self.frontend.stdout.name, self.frontend.stderr.name)

    def _printInstalCompleted(self, stdoutFilename, stderrFilename):
        printStep('Installation completed')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (stdoutFilename, stderrFilename)
    
    def _assignDrivers(self):
        self.infoDriver = (True and self.infoDriver) or ('im_%s' % self.hypervisor)
        self.virtDriver = (True and self.virtDriver) or ('vmm_%s' % self.hypervisor)
        self.transfertDriver = (True and self.transfertDriver) or ('tm_%s' % self.shareType)

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

    def _addCloudNode(self):
        # This just assumes that a node can't be added because it exists
        # already.  A better implementation would check to see if it 
        # really does exists and if so, returns the existing node id.
        try:
            return self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver)
        except OneException:
            Util.printWarning('Couldn\'t add host, already present?')
            # The id is actually ignored, so this should be ok.
            return -1
        
    def _installCAs(self):
        self.frontend.installCAs()

    def _setFrontend(self):
        if not self.frontendIp or self.frontendIp == '127.0.0.1':
            printWarning('frontend_ip configuration parameter is %s, this is very likely not to work' % self.frontendIp)
        self.frontend = SystemFactory.getSystem(self.frontendSystem, self.configHolder)

    def _configureCloudAdminNode(self):
        self.node.configureCloudAdminSshKeysNode()
        self.node.configureCloudAdminSudoNode()
        self.node.configureCloudAdminPdiskNode()

    def _configureQuarantine(self):
        self.frontend.configureQuarantine()
        
    def _configureCloudProxyService(self):
        self.frontend.configureCloudProxyService()

    def _configureRegistrationApplication(self):
        # TODO: Split install
        if self._isTrue(self.registration):
            Registration(self.configHolder).run()

    def _configureMarketPlacePolicyValidation(self):
        # TODO: Split install
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
        
    def _configureBridgeOnNode(self):
        self.node.configureBridgeRemotely()
        
    def _removeCloudNode(self, nodeId):
        self.cloud.hostRemove(nodeId)
        
    def _addDefaultNetworks(self):
        for vnet in self.defaultStaticNetworks:
            try:
                self.cloud.networkCreate(self._buildFixedNetworkTemplate(vnet))
            except OneException, ex:
                Util.printWarning("Couldn't create virtual network. Already present? %s" % str(ex))
        for vnet in self.defaultRangedNetworks:
            try:
                self.cloud.networkCreate(self._buildRangedNetworkTemplate(vnet))
            except OneException, ex:
                Util.printWarning("Couldn't create virtual network. Already present? %s" % str(ex))

    def _addDefaultAcls(self):
        self._addDefaultNetworkAcl()
        self._addDefaultUserAcl()

    def _addDefaultNetworkAcl(self):
        # * NET/#<id> USE (allow to use all networks by all users)
        for net_id in [0, 1, 2]:
            try:
                self.cloud.addNetworkAcl(hex(self.cloud.ACL_USERS['ALL']),
                                         net_id,
                                         hex(self.cloud.ACL_RIGHTS['USE']))
            except OneException, ex:
                Util.printWarning("Couldn't add ACL on NET %i: %s" % (net_id, str(ex)))

    def _addDefaultUserAcl(self):
        # * VM+IMAGE+TEMPLATE/* CREATE+INFO_POOL_MINE+INSTANTIATE
        __acls = '* VM+IMAGE+TEMPLATE/* CREATE+INFO_POOL_MINE+INSTANTIATE'

        users = hex(self.cloud.ACL_USERS['ALL'])
        resources = hex(self.cloud.ACL_RESOURCES['VM'] +
                        self.cloud.ACL_RESOURCES['IMAGE'] +
                        self.cloud.ACL_RESOURCES['TEMPLATE'] +
                        self.cloud.ACL_USERS['ALL'])
        rights = hex(self.cloud.ACL_RIGHTS['CREATE'] + 
                    self.cloud.ACL_RIGHTS['INFO_POOL_MINE'] +
                    self.cloud.ACL_RIGHTS['INSTANTIATE'])
        try:
            self.cloud.addUserAcl(users, resources, rights)
        except OneException, ex:
                Util.printWarning("Couldn't add default user ACL [%s]. %s" % \
                                  (__acls, str(ex)))

    def _buildFixedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(os.path.join(Defaults.SHARE_DIR, 'vnet/fixed.net'))
        
        ips = self.config.get('one_%s_network_addr' % networkName)
        ips = (ips and ips.split(' ')) or []
        
        macs = self.config.get('one_%s_network_mac' % networkName)
        macs = (macs and macs.split(' ')) or []
        
        leases = ['LEASES = [ IP="%s", MAC="%s"]' % (ip, mac) for ip, mac in zip(ips, macs)]

        vnetTpl = vnetTpl % ({'network_name': networkName,
                              'bridge': self.config.get('node_bridge_name'),
                              'leases': '\n'.join(leases)})
        return vnetTpl

    def _buildRangedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(os.path.join(Defaults.SHARE_DIR, 'vnet/ranged.net'))
        vnetTpl = vnetTpl % ({'network_name': networkName,
                              'bridge': self.config.get('node_bridge_name'),
                              'network_size': self.config.get('one_%s_network_size' % networkName),
                              'network_addr': self.config.get('one_%s_network' % networkName)})
        return vnetTpl

    def _configurePolicies(self):
        oneAuthTpl = os.path.join(Util.getTemplateDir(), 'quota.conf.tpl')
        if not os.path.isfile(oneAuthTpl):
            Util.printError('ONE auth configuration template '
                       '%s does not exists' % oneAuthTpl)

        authConfFile = self.cloudConfDir + 'auth/quota.conf'

        # need KB
        try:
            quotaMemory = int(self.quotaMemory)
        except ValueError:            
            quotaMemory = self.quotaMemory.strip()
            if(self.quotaMemory.upper().endswith('GB')):
                quotaMemory = int(quotaMemory[:-2])*(1024**2)
            elif(quotaMemory.upper().endswith('MB')):
                quotaMemory = int(quotaMemory[:-2])*1024
            elif(quotaMemory.upper().endswith('KB')):
                quotaMemory = int(quotaMemory[:-2])
            else:
                raise

        self.quotaMemoryKB = quotaMemory

        self.frontend.filePutContentsCmd(authConfFile,
                                         fileGetContent(oneAuthTpl) % self.__dict__)

    def _configureCloudSystem(self):
        self.__configureOneDaemon()

    def __configureOneDaemon(self):
        if not os.path.isfile(self.onedTpl):
            Util.printError('ONe daemon configuration template '
                            '%s does not exists' % self.onedTpl)

        conf = self.config.copy()
        conf['vm_dir'] = self.cloudVarLibDir
        self.frontend.filePutContentsCmd(self.cloudConfFile,
                                         fileGetContent(self.onedTpl) % conf)
    
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
        elif self.shareType == 'stratuslab':
            self.frontend.configureSshServer()

    # ---- NFS configuration

    def _configureNfsServer(self):
        mountPoint = self.cloudVarLibDir
        if self._nfsShareAlreadyExists():
            self.frontend.configureExistingNfsShare(self.config.get('existing_nfs'), mountPoint)
        else:
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
            self.node.configureSshClient(self.cloudVarLibDir)
        elif self.shareType == 'stratuslab':
            self.node.configureSshClient(self.cloudVarLibDir)
    
    # ---- NFS configuration   
         
    def _configureNfsClient(self):
        mountPoint = self.cloudVarLibDir
        if self._nfsShareAlreadyExists():
            host = self.config.get('existing_nfs')
        else:
            host = '%s:%s' % (self.config['frontend_ip'], self.cloudVarLibDir)

        self.node.configureExistingNfsShare(host, mountPoint)
