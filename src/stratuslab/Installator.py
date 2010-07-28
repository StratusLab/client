import os
import sys

import stratuslab
from Util import filePutContents
from Util import fileGetContents 
from Util import parseConfig

class Installator(object):

    def __init__(self, options):
        self.modulePath = os.path.abspath('%s/../' % os.path.abspath(os.path.dirname(stratuslab.__file__)))
        
        self.configFile = options.configFile
        self.config = parseConfig(self.configFile)
        
        # Default network added automatically at installation
        # Make sure one_%(name)s_* exist in the config 
        self.defaultNetworks = ['private', 'public']    
        
        self.nodeAddr = options.nodeAddr
        
        self.onedConfTemplate = options.onedTpl

        # Path to the system directory 
        self.systemsDir = '%s/stratuslab/system' % self.modulePath
        
        self.shareType = self.config.get('share_type')
        
        # TODO: Automatically determine system
        self.frontend = self.getSystemMethods(self.config.get('frontend_system'))
        self.node = self.getSystemMethods(self.config.get('node_system'))
        
        self.privateKey = (True and options.privateKey) or (
            self.config['node_private_key'])
        self.infoDriver = (True and options.infoDriver) or ('im_%s' %
            self.config['hypervisor'])
        self.virtDriver = (True and options.virtDriver) or ('vmm_%s' %
            self.config['hypervisor'])
        self.transfertDriver = (True and options.transfertDriver) or (
            'tm_%s' % self.config['share_type'])

    def setPythonPath(self, path):
        if not path in sys.path:
            sys.path.append(path)

    def getSystemMethods(self, system):
        if not os.path.isfile('%s/%s.py' % (self.systemsDir, system)):
            raise ValueError('Specified system %s not available' %
                system)

        self.setPythonPath(self.systemsDir)

        module = self.importSystem(system)
        return getattr(module, 'system')

    def importSystem(self, system):
        module = None
        try:
            module = __import__(system)
        except:
            print 'Error while importing system module'
            sys.exit(1)
        else:
            return module

    def propagateNodeInfos(self):
        self.node.setNodeAddr(self.nodeAddr)
        self.node.setNodePrivateKey(self.privateKey)
        self.node.setNodePort(self.config.get('node_ssh_port'))
        self.node.setNodeHypervisor(self.config.get('hypervisor'))
        self.node.workOnNode()
        self.frontend.setONeAdmin(self.config.get('one_username'))

    def createONeAdmin(self, system):
        system.createONeGroup(self.config.get('one_group'),
                              self.config.get('one_gid'))
        system.createONeAdmin(self.config.get('one_username'),
                              self.config.get('one_uid'), 
                              self.config.get('one_home'),
                              self.config.get('one_password'))

    def configureONeAdminNode(self):
        self.node.configureNetwork(self.config.get('node_network_interface'),
                                   self.config.get('node_bridge_name'))
        self.node.configureNodeSshCred()

    def configureONeAdminFrontend(self):
        self.frontend.configureONeAdminEnv(self.config.get('one_port'))
        self.frontend.configureONeAdminAuth()
        self.frontend.setupONeAdminSSHCred()

    def installONe(self):
        self.frontend.installFrontendDependencies()
        self.frontend.cloneGitRepository(self.config.get('one_build_dir'),
                                         self.config.get('one_git_repo'), 
                                         self.config.get('one_clone_name'),
                                         self.config.get('one_branch'))  
        self.frontend.buildOpenNebula()
        self.frontend.installOpenNebula()

    def addONeNode(self):
        # TODO: Use XML RPC methods
        self.frontend.ONeAdminExecute(['onehost create %s %s %s %s' % 
            (self.nodeAddr, self.infoDriver, self.virtDriver,
            self.transfertDriver)
        ])
        
    def addDefaultNetwork(self):
        # TODO: Use XML RPC methods
        for vnet in self.defaultNetworks:
            vnetTpl = '/tmp/stratus-vnet'
            if self.config.get('one_%s_network_addr' % vnet, '') == '':
                filePutContents(vnetTpl, self.buildRangedNetworkTemplate(vnet))
            else:
                filePutContents(vnetTpl, self.buildFixedNetworkTemplate(vnet))
            self.frontend.ONeAdminExecute(['onevnet create %s' % vnetTpl])
        
    def buildFixedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContents('%s/share/vnet/fixed.net' % self.modulePath)
        vnetTpl = vnetTpl % ({'network_name': networkName,
                              'bridge': self.config.get('node_bridge_name'),
                              'leases': '\n'.join(['LEASES = [ IP="%s"]' % i 
                                         for i in self.config.get('one_%s_network_addr' % networkName).split(' ')])})
        return vnetTpl
    
    def buildRangedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContents('%s/share/vnet/ranged.net' % self.modulePath)
        vnetTpl = vnetTpl % ({'network_name': networkName,
                              'bridge': self.config.get('node_bridge_name'),
                              'network_size': self.config.get('one_%s_network_size' % networkName),
                              'network_addr': self.config.get('one_%s_network' % networkName)})
        return vnetTpl
        
    def setupFileSharingServer(self):
        self.frontend.installPackages(self.frontend.fileSharingFrontendDeps.get(self.shareType, []))
        self.configureFileSharingServer()

    def configureFileSharingServer(self):
        if self.shareType == 'nfs':
            self.configureNfsServer()
        elif self.shareType == 'ssh':
            self.frontend.configureSSHServer()

    def configureNfsServer(self):
        if self.nfsShareAlreadyExists():
            self.frontend.configureNfsShare(self.config.get('existing_nfs'), 
                                            self.getNfsDefaultMountPoint())
        else:
            self.frontend.configureNFSServer(self.getNfsDefaultMountPoint(),
                                             self.config['network_addr'],
                                             self.config['network_mask'])

    def nfsShareAlreadyExists(self):
        return not (self.config.get('existing_nfs', '') == '')

    def getNfsDefaultMountPoint(self):
        return os.path.dirname(self.config.get('one_home'))

    def setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(self.shareType, []))
        self.configureFileSharingClient()

    def configureFileSharingClient(self):
        if self.shareType == 'nfs':
            self.configureNfsClient()
        elif self.shareType == 'ssh':
            self.frontend.configureSSHClient()
            
    def configureNfsClient(self):
        if self.nfsShareAlreadyExists():
            host = self.config.get('existing_nfs')
        else:
            host = '%s:%s' % (self.config['frontend_ip'], 
                              self.getNfsDefaultMountPoint())

        self.node.configureNfsShare(host, self.getNfsDefaultMountPoint())

    def configureONeDaemon(self):
        if not os.path.isfile(self.onedConfTemplate):
            raise ValueError('ONe daemon configuration template '
                '%s does not exists' % self.onedConfTemplate)
    
        filePutContents('%s/etc/oned.conf' % self.config['one_home'],
                        fileGetContents(self.onedConfTemplate) % self.config)

    def startONeDaemon(self):
        self.frontend.startONeDaemon()

    def nodeAlive(self):
        return self.node.nodeShell('exit 0') == 0

    def installNodeDependencies(self):
        self.node.installNodeDependencies()
        self.node.installHypervisor()
        self.node.configureHypervisor()
