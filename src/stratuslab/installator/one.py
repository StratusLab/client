import os
import os.path

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

        if self.config.get('vm_dir') != '':
            self.frontend.createDirsCmd(self.config.get('vm_dir'))
            self.frontend.setOwnerCmd(self.config.get('vm_dir'))
        
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

        conf = self.config.copy()
        if conf.get('vm_dir') == '':
            conf['vm_dir'] = '%s/var' % conf.get('one_home')

        filePutContent('%s/etc/oned.conf' % self.config.get('one_home'),
                       fileGetContent(self.onedConfTemplate) % conf)
    
    def addCloudNode(self):
        self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver)
        
    def addDefaultNetworks(self):
        for vnet in self.defaultNetworks:
            if self.config.get('one_%s_network_addr' % vnet, '') == '':
                self.cloud.networkCreate(self._buildRangedNetworkTemplate(vnet))
            else:
                self.cloud.networkCreate(self._buildFixedNetworkTemplate(vnet))
        
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
        self.frontend.filePutContentsCmd('%s/share/scripts/init.sh' % oneHome,
                fileGetContent('%s/share/context/init.sh' % modulePath))

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