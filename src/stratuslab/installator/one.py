import os

from stratuslab.BaseInstallator import BaseInstallator
from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import modulePath
from stratuslab.Util import printError

class OneInstallator(BaseInstallator):
    
    def runInstall(self, options, config):
        self.privateKey = (True and options.privateKey) or (config.get('node_private_key'))
        self.infoDriver = (True and options.infoDriver) or ('im_%s' % config.get('hypervisor'))
        self.virtDriver = (True and options.virtDriver) or ('vmm_%s' % config.get('hypervisor'))
        self.transfertDriver = (True and options.transfertDriver) or ('tm_%s' % config.get('share_type'))
        
        self.onedConfTemplate = options.onedTpl

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(self.config.get('one_username'),
                                  self.config.get('one_password'))
        
        super(OneInstallator, self).runInstall(options, config)
        
    # -------------------------------------------
    #    Cloud admin management
    # -------------------------------------------
    
    def createCloudAdmin(self, system):
        system.createCloudGroup(self.config.get('one_group'),
                                self.config.get('one_gid'))
        system.createCloudAdmin(self.config.get('one_username'),
                                self.config.get('one_uid'),
                                self.config.get('one_home'),
                                self.config.get('one_password'))

    def configureCloudAdminNode(self):
        self.node.configureNetwork(self.config.get('node_network_interface'),
                                   self.config.get('node_bridge_name'))
        self.node.configureCloudAdminSshKeysNode()

    def configureCloudAdminFrontend(self):
        self.frontend.configureCloudAdminEnv(self.config.get('one_port'))
        self.frontend.configureCloudAdminAccount()
        self.frontend.configureCloudAdminSshKeys()
        
    # -------------------------------------------
    #    Cloud installation management
    # -------------------------------------------

    def installCloudSystem(self):
        self.frontend.installFrontendDependencies()
        self.frontend.cloneGitRepository(self.config.get('one_build_dir'),
                                         self.config.get('one_git_repo'),
                                         self.config.get('one_clone_name'),
                                         self.config.get('one_branch'))
        self.frontend.buildCloudSystem()
        self.frontend.installCloudSystem()
        self._copyContextualizationScript(self.config.get('one_home'))
        
    # -------------------------------------------
    #    Cloud configuration management
    # -------------------------------------------

    def configureCloudSystem(self):
        if not os.path.isfile(self.onedConfTemplate):
            printError('ONe daemon configuration template '
                       '%s does not exists' % self.onedConfTemplate)
    
        filePutContent('%s/etc/oned.conf' % self.config.get('one_home'),
                       fileGetContent(self.onedConfTemplate) % self.config)
    
    def addCloudNode(self):
        self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver)
        
    def addDefaultNetworks(self):
        for vnet in self.defaultNetworks:
            if self.config.get('one_%s_network_addr' % vnet, '') == '':
                self.cloud.networkCreate(self._buildRangedNetworkTemplate(vnet))
            else:
                self.cloud.networkCreate(self._buildFixedNetworkTemplate(vnet))
                
            self.frontend._cloudAdminExecute(['onevnet create %s' % vnetTpl])
            os.remove(vnetTpl)
        
    def _buildFixedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent('%s/share/vnet/fixed.net' % modulePath)
        
        leases = ['LEASES = [ IP="%s"]' % i for i in self.config.get('one_%s_network_addr' % networkName).split(' ')]
        
        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'leases': '\n'.join(leases)})
        return vnetTpl
    
    def _buildRangedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent('%s/share/vnet/ranged.net' % modulePath)
        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'network_size': self.config.get('one_%s_network_size' % networkName),
                             'network_addr': self.config.get('one_%s_network' % networkName)})
        return vnetTpl

    def _copyContextualizationScript(self, oneHome):
        self.frontend.createDirsCmd('%s/share/scripts/' % oneHome)
        self.frontend.filePutContentsCmd('%s/share/scripts/init.sh' % oneHome, fileGetContent('%s/share/one/init.sh' % modulePath))

    # -------------------------------------------
    #   Front-end file sharing management
    # -------------------------------------------
    
    def setupFileSharingServer(self):
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
            self.frontend.configureExistingNfsShare(self.config.get('existing_nfs'), 
                                                    self._getNfsDefaultMountPoint())
        else:
            self.frontend.configureNewNfsServer(self._getNfsDefaultMountPoint(),
                                                self.config['network_addr'],
                                                self.config['network_mask'])

    def _nfsShareAlreadyExists(self):
        return not (self.config.get('existing_nfs', '') == '')

    def _getNfsDefaultMountPoint(self):
        return os.path.dirname(self.config.get('one_home'))
    
    # -------------------------------------------
    #    Node file sharing management
    # -------------------------------------------

    def setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(self.shareType, []))
        self._configureFileSharingClient()

    def _configureFileSharingClient(self):
        if self.shareType == 'nfs':
            self._configureNfsClient()
        elif self.shareType == 'ssh':
            self.frontend.configureSshClient()
    
    # ---- NFS configuration   
         
    def _configureNfsClient(self):
        if self._nfsShareAlreadyExists():
            host = self.config.get('existing_nfs')
        else:
            host = '%s:%s' % (self.config['frontend_ip'], 
                              self._getNfsDefaultMountPoint())

        self.node.configureExistingNfsShare(host, self._getNfsDefaultMountPoint())
