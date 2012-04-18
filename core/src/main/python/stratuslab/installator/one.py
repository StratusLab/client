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

from BaseInstallator import BaseInstallator
from stratuslab.Util import fileGetContent
import stratuslab.Util as Util
from stratuslab.Exceptions import OneException, ExecutionException
from stratuslab import Defaults
from stratuslab.installator.OneDefaults import OneDefaults

etree = Util.importETree()

class OneInstallator(BaseInstallator):
    
    def __init__(self):
        super(OneInstallator, self).__init__()
        self.cloudConfDir = OneDefaults.CLOUD_CONF_DIR
        self.cloudConfFile = OneDefaults.CLOUD_CONF_FILE

    def _addCloudNode(self):
        # This just assumes that a node can't be added because it exists
        # already.  A better implementation would check to see if it 
        # really does exists and if so, returns the existing node id.
        try:
            return self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver, self.networkDriver)
        except OneException:
            Util.printWarning('Couldn\'t add host, already present?')
            # The id is actually ignored, so this should be ok.
            return -1
        
    def _removeCloudNode(self, id):
        self.cloud.hostRemove(id)
        
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
        for net_id in self._getVnetIdsFromVnetNames():
            try:
                self.cloud.addNetworkAcl(hex(self.cloud.ACL_USERS['ALL']),
                                         net_id,
                                         hex(self.cloud.ACL_RIGHTS['USE']))
            except OneException, ex:
                Util.printWarning("Couldn't add ACL on NET %i: %s" % (net_id, str(ex)))

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
