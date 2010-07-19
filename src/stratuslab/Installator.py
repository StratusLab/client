import os
import sys

from Util import filePutContents
from Util import fileGetContents 
from Util import parseConfig

class Installator(object):
    # Path to the systems directory 
    specsFilesDir = '%(currentDir)s/system'

    def __init__(self, options):
        self.configFile = options.configFile
        self.nodeAddr = options.nodeAddr
        self.ONeDConfTemplateFile = options.onedTpl

        self.specsFilesDir = self.specsFilesDir % ({
            'currentDir': os.path.abspath(os.path.dirname(__file__))
        })
        self.config = parseConfig(self.configFile)
        self.frontend = self.getSystemMethods(
            self.config['frontend_system'])
        self.node = self.getSystemMethods(self.config['node_system'])
        
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
        if not os.path.isfile('%s/%s.py' % (self.specsFilesDir, system)):
            raise ValueError('Specified system %s not available' %
                system)

        self.setPythonPath(self.specsFilesDir)

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
        self.node.setNodePort(self.config['node_ssh_port'])
        self.node.setNodeHypervisor(self.config['hypervisor'])
        self.node.workOnNode()
        self.frontend.setONeAdmin(self.config['one_username'])
        print dir(self.frontend)

    def createONeAdmin(self, system):
        system.createONeGroup(self.config['one_group'],
                              self.config['one_gid'])
        system.createONeAdmin(self.config['one_username'],
                              self.config['one_uid'], 
                              self.config['one_home'],
                              self.config['one_password'])

    def configureONeAdminNode(self):
        self.node.configureNodeSshCred()

    def configureONeAdminFrontend(self):
        self.frontend.configureONeAdminEnv(self.config['one_port'])
        self.frontend.configureONeAdminAuth()
        self.frontend.setupONeAdminSSHCred()

    def installONe(self):
        self.frontend.installFrontendDependencies()
        self.frontend.cloneGitRepository(self.config['one_build_dir'],
                                         self.config['one_git_repo'], 
                                         self.config['one_clone_name'],
                                         self.config['one_branch'])  
        self.frontend.buildOpenNebula()
        self.frontend.installOpenNebula()

    def addONeNode(self):
        self.frontend.ONeAdminExecute(['onehost create %s %s %s %s' % 
            (self.nodeAddr, self.infoDriver, self.virtDriver,
            self.transfertDriver)
        ])
        
    def setupFileSharingServer(self):
        self.frontend.installPackages(self.frontend.fileSharingFrontendDeps.get(
            self.config['share_type'], []))
        self.configureFileSharingServer()

    def configureFileSharingServer(self):
        if self.config['share_type'] == 'nfs':
            self.configureNfsServer()
        elif self.config['share_type'] == 'ssh':
            self.frontend.configureSSHServer()

    def configureNfsServer(self):
        if self.nfsExists():
            self.frontend.configureNfsShare(self.config['existing_nfs'], 
                self.getNfsDefaultMountPoint())
        else:
            self.frontend.configureNFSServer(self.getNfsDefaultMountPoint(),
                                             self.config['network_addr'],
                                             self.config['network_mask'])

    def nfsExists(self):
        return not (self.config.get('existing_nfs', '') == '')

    def getNfsDefaultMountPoint(self):
        return os.path.dirname(self.config['one_home'])

    def setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(
            self.config['share_type'], []))
        self.configureFileSharingClient()

    def configureFileSharingClient(self):
        if self.config['share_type'] == 'nfs':
            self.configureNfsClient()
        elif self.config['share_type'] == 'ssh':
            self.frontend.configureSSHClient()
            
    def configureNfsClient(self):
        if self.nfsExists():
            host = self.config['existing_nfs']
        else:
            host = '%s:%s' % (self.config['frontend_ip'], 
                self.getNfsDefaultMountPoint())

        self.node.configureNfsShare(host, self.getNfsDefaultMountPoint())

    def configureONeDaemon(self):
        if not os.path.isfile(self.ONeDConfTemplateFile):
            raise ValueError('ONe daemon configuration template '
                '%s does not exists' % self.ONeDConfTemplateFile)

        ONeDConfTemplate = fileGetContents(self.ONeDConfTemplateFile)         
        filePutContents('%s/var/oned.conf' % self.config['one_home'],
            ONeDConfTemplate % self.config)
        self.frontend.setONeAdminOwner('%s/var/oned.conf' %
            self.config['one_home'])

    def startONeDaemon(self):
        self.frontend.startONeDaemon()

    def nodeAlive(self):
        return self.node.nodeShell('exit 0') == 0

    def installNodeDependencies(self):
        self.node.installNodeDependencies()
        self.node.installHypervisor()
        self.node.configureHypervisor()
