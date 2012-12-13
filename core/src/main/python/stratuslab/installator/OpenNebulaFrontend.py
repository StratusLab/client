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
from stratuslab.Exceptions import OneException, ExecutionException
from stratuslab.Util import printWarning, fileGetContent, printError,\
    getTemplateDir, getValueInKB
from stratuslab import Defaults
from os.path import join, isfile
import stratuslab.Util as Util
from stratuslab.system import SystemFactory

etree = Util.importETree()

class OpenNebulaFrontend(OpenNebulaCommon):
    
    def __init__(self, configHolder):
        super(OpenNebulaFrontend, self).__init__(configHolder)
        self.cloudConfDir = Defaults.CLOUD_CONF_DIR
        self.cloudConfFile = Defaults.CLOUD_CONF_FILE
        self.cloudVarLibDir = Defaults.CLOUD_VAR_LIB_DIR
        self.defaultStaticNetworks = ['public', 'local']
        self.defaultRangedNetworks = ['private']
        
        self._setFrontendSystem()

    def _setFrontendSystem(self):
        if not self.frontendIp or self.frontendIp == '127.0.0.1':
            printWarning('frontend_ip configuration parameter is %s, this is very likely not to work' % self.frontendIp)
        self.frontend = SystemFactory.getSystem(self.frontendSystem, self.configHolder)

    def _installCAs(self):
        self.frontend.installCAs()

    def _installSendmail(self):
        self.frontend.installSendmail()
        
    def _configureQuarantine(self):
        self.frontend.configureQuarantine()
        
    def _configureCloudProxyService(self):
        self.frontend.configureCloudProxyService()
        
    def _configureFirewall(self):
        self.frontend.configureFirewall()

    def _configureDhcpServer(self):
        self.frontend.configureDhcpServer()

    def _configureDatabase(self):
        self.frontend.configureDatabase()

    def _configureCloudAdminFrontend(self):
        self.frontend.configureCloudAdminAccount()
        self.frontend.configureCloudAdminSshKeys()
    
    def _startServicesFrontend(self):
        self.frontend.startCloudSystem()

    def _addDefaultNetworks(self):
        self._createNetwork(self.defaultStaticNetworks, self._buildFixedNetworkTemplate)
        self._createNetwork(self.defaultRangedNetworks, self._buildRangedNetworkTemplate)
        
    def _createNetwork(self, networks, builder):
        for vnet in networks:
            try:
                self.cloud.networkCreate(builder(vnet))
            except OneException as ex:
                printWarning("Couldn't create virtual network. Already present? %s" % str(ex))

    def _buildFixedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(join(Defaults.SHARE_DIR, 'vnet/fixed.net'))
        
        ips = self._getIPs(networkName)
        macs = self._getMACs(networkName)
        leases = ['LEASES = [ IP="%s", MAC="%s"]' % (ip, mac) for ip, mac in zip(ips, macs)]

        vnetTpl = vnetTpl % ({'network_name': networkName,
                              'bridge': self.config.get('node_bridge_name'),
                              'leases': '\n'.join(leases)})
        return vnetTpl
    
    def _getIPs(self, networkName):
        ips = self.config.get('one_%s_network_addr' % networkName)
        return ips and ips.split(' ') or []

    def _getMACs(self, networkName):
        macs = self.config.get('one_%s_network_mac' % networkName)
        return macs and macs.split(' ') or []
    
    def _buildRangedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(join(Defaults.SHARE_DIR, 'vnet/ranged.net'))
        vnetTpl = vnetTpl % ({'network_name': networkName,
                              'bridge': self.config.get('node_bridge_name'),
                              'network_size': self.config.get('one_%s_network_size' % networkName),
                              'network_addr': self.config.get('one_%s_network' % networkName)})
        return vnetTpl
    
    def _addDefaultAcls(self):
        self._addDefaultNetworkAcl()
        self._addDefaultUserAcl()

    def _addDefaultNetworkAcl(self):
        # * NET/#<id> USE (allow to use all networks by all users)
        for net_id in self._getVnetIdsFromVnetNames():
            try:
                self.cloud.addNetworkAcl(hex(self.cloud.ACL_USERS['ALL']),
                                         net_id,
                                         hex(self.cloud.ACL_RIGHTS['USE']))
            except OneException, ex:
                printWarning("Couldn't add ACL on NET %i: %s" % (net_id, str(ex)))

    def _getVnetIdsFromVnetNames(self):
        net_ids = []
        for vnet_name in self.defaultStaticNetworks + self.defaultRangedNetworks:
            vnet_id = self._getVnetIdFromVnetName(vnet_name)
            net_ids.append(int(vnet_id))

        return net_ids
    
    def _getVnetIdFromVnetName(self, vnet_name):
            vnet_info = self._getVnetInfoXml(vnet_name)
            try:
                vnet_tree = etree.fromstring(vnet_info)
            except SyntaxError, ex:
                raise ExecutionException('Unable to parse vnet %s info: %s' % 
                                         (vnet_name, str(ex)))
            try:
                vnet_id = vnet_tree.find('ID').text
            except Exception, ex:
                raise ExecutionException("Failed to find ID of vnet %s in %s with %s" %
                                         (vnet_name, vnet_info, str(ex)))
            if not vnet_id:
                raise ExecutionException("Failed to find ID of vnet %s in %s." %
                                         (vnet_name, vnet_info))

            return vnet_id

    @staticmethod
    def _getVnetInfoXml(vnet_name):
        rc, output = Util.execute(['onevnet', 'show', '--xml', vnet_name], 
                                  withOutput=True)
        if rc != 0:
            raise ExecutionException("Couldn't get network info for network '%s'." % vnet_name)

        return output

    def _addDefaultUserAcl(self):
        # * VM+IMAGE+TEMPLATE/* CREATE+INFO_POOL_MINE+INSTANTIATE
        __acls = '* VM+IMAGE+TEMPLATE/* CREATE+USE'
        users,resources, rights = self._getDefaultUserAcl()
        
        try:
            self.cloud.addUserAcl(users, resources, rights)
        except OneException, ex:
            printWarning("Couldn't add default user ACL [%s]. %s" % (__acls, str(ex)))
            
    def _getDefaultUserAcl(self):
        users = hex(self.cloud.ACL_USERS['ALL'])
        resources = hex(self.cloud.ACL_RESOURCES['VM'] +
                        self.cloud.ACL_RESOURCES['IMAGE'] +
                        self.cloud.ACL_RESOURCES['TEMPLATE'] +
                        self.cloud.ACL_USERS['ALL'])
        rights = hex(self.cloud.ACL_RIGHTS['CREATE'] + 
                    self.cloud.ACL_RIGHTS['USE'])
        return users, resources, rights
            
    def _configureCloudSystem(self):
        self._configureOneDaemon()

    def _configureOneDaemon(self):
        onedTpl = self._getTemplateFile('oned.conf.tpl', 'ONe daemon configuration')
        conf = self.config.copy()
        conf['vm_dir'] = self.cloudVarLibDir
        self.frontend.filePutContentsCmd(self.cloudConfFile,
                                         fileGetContent(onedTpl) % conf)

    def _configurePolicies(self):
        oneAuthTpl = self._getTemplateFile('quota.conf.tpl', 'ONE auth configuration')
        authConfFile = self.cloudConfDir + 'auth/quota.conf'
        
        self.quotaMemoryKB = getValueInKB(self.quotaMemory)
        self.frontend.filePutContentsCmd(authConfFile,
                                         fileGetContent(oneAuthTpl) % self.__dict__)
        
    def _getTemplateFile(self, tpl, name):
        tplPath = join(getTemplateDir(), tpl)
        if not isfile(tplPath):
            printError('%s template %s does not exists' % (name, tplPath))
        return tplPath
        
        
    def _setupFileSharingServer(self):
        self.frontend.installPackages(self.frontend.fileSharingFrontendDeps.get(self.shareType, []))
        self._configureFileSharingServer()

    def _configureFileSharingServer(self):
        if self.shareType == 'nfs':
            self._configureNfsServer()
        elif self.shareType in ('ssh', 'stratuslab'):
            self.frontend.configureSshServer()
        else:
            printError('Unable to determine frontend share type. Got %s' % self.shareType)

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
    