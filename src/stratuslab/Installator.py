# -*- coding: utf-8 -*-
import os
import sys
from ConfigParser import SafeConfigParser

from stratuslab.Util import defaultConfigSection
from stratuslab.Util import validConfiguration
from stratuslab.Util import filePutContents
from stratuslab.Util import fileGetContents 

class Installator(object):
    # Path to the systems directory 
    specsFilesDir = '%(currentDir)s/system'

    def __init__(self, options):
        self.configFile = options.configFile
        self.verbose = options.verbose
        self.quiet = options.quiet
        self.nodeAddr = options.nodeAddr
        self.ONeDConfTemplateFile = options.onedTpl

        self.specsFilesDir = self.specsFilesDir % ({
            'currentDir': os.path.abspath(os.path.dirname(__file__))
        })
        self.config = self.parseConfig(self.configFile)
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

        module = __import__(system)
        return getattr(module, 'system')

    def parseConfig(self, configFile):
        if not os.path.isfile(configFile):
            raise ValueError('Configuration file %s does not exists' %
                configFile)

        config = SafeConfigParser()
        config.read(configFile)    
        validConfiguration(config)
        return dict(config.items(defaultConfigSection))

    def propagateNodeInfos(self):
        self.node.setNodeAddr(self.nodeAddr)
        self.node.setNodePrivateKey(self.privateKey)
        self.node.setNodePort(self.config['node_ssh_port'])
        self.node.setNodeHypervisor(self.config['hypervisor'])

    def createONeAdmin(self, system):
        system.createONeGroup(self.config['one_group'],
                              self.config['one_gid'])
        system.createONeAdmin(self.config['one_username'],
                              self.config['one_uid'], 
                              self.config['one_home'],
                              self.config['one_password'])

    def configureONeAdmin(self):
        self.frontend.configureONeAdminEnv()
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
            (self.infoDriver, self.virtDriver, self.transfertDriver)])
        
    def setupFileSharingServer(self):
        self.frontend.installPackages(self.frontend.fileSharingFrontendDeps.get(
            self.config['share_type'], []))
        self.configureFileSharingServer()

    def configureFileSharingServer(self):
        if self.config['share_type'] == 'nfs':
            self.frontend.configureNFSServer(self.config['network_addr'],
                                             self.config['network_mask'])
        elif self.config['share_type'] == 'ssh':
            self.frontend.configureSSHServer()

    def setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(
            self.config['share_type'], []))
        self.configureFileSharingClient()

    def configureFileSharingClient(self):
        if self.config['share_type'] == 'nfs':
            self.frontend.configureNFSClient(self.config['frontend_ip'])
        elif self.config['share_type'] == 'ssh':
            self.frontend.configureSSHClient()

    def configureONeDaemon(self):
        if not os.path.isfile(self.ONeDConfTemplateFile):
            raise ValueError('ONe daemon configuration template '
                '%s does not exists' % ONeDConfTemplateFile)

        ONeDConfTemplate = fileGetContents(self.ONeDConfTemplateFile)         
        filePutContents('%s/var/oned.conf' % self.config['one_home'],
            ONeDConfTemplate % self.config)
        self.frontend.setONeAdminOwner('%s/var/oned.conf' %
            self.config['one_home'])

    def startONeDaemon(self):
        self.frontend.startONeDaemon()

    def checkConnectivity(self, hostAddr):
        return self.node.nodeShell('exit 0')

    def installNodeDependencies(self):
        self.node.installNodeDependencies()
        self.node.installHypervisor()
        self.node.configureHypervisor()

