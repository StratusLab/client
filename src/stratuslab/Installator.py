# -*- coding: utf-8 -*-
import os
import sys
from ConfigParser import SafeConfigParser

from stratuslab.Util import defaultConfigSection
from stratuslab.Util import validConfiguration
from stratuslab.Util import filePutContents
from stratuslab.Util import fileGetContents 

class Installator(object):
    # Directory where file for each OS are stored
    specsFilesDir = '%(currentDir)s/arch'

    def __init__(self, options):
        self.configFile = options.configFile
        self.verbose = options.verbose
        self.quiet = options.quiet
        self.ONeDConfTemplateFile = options.onedTpl
        self.specsFilesDir = self.specsFilesDir % ({
            'currentDir': os.path.abspath(os.path.dirname(__file__))
        })

        if not os.path.isfile(self.configFile):
            raise ValueError('Configuration file does not exists')

        self.config = self.parseConfig(self.configFile)
        self.loadMachineSpecs()

    def setPythonPath(self, path):
        if not path in sys.path:
            sys.path.append(path)

    def loadMachineSpecs(self):
        self.frontendOS = self.config.get('frontend_os')

        if not os.path.isfile('%s/%s.py' 
                % (self.specsFilesDir, self.frontendOS)):
            raise ValueError('Specified front-end OS not available')

        self.setPythonPath(self.specsFilesDir)

        module = __import__(self.frontendOS)
        self.machine = getattr(module, 'machine')

    def parseConfig(self, configFile):
        config = SafeConfigParser()
        config.read(configFile)    
        validConfiguration(config)
        return dict(config.items(defaultConfigSection))

    def setupONeAdmin(self):
        self.machine.createONeGroup(self.config['one_group'],
                                    self.config['one_gid'])
        self.machine.createONeAdmin(self.config['one_username'],
                                    self.config['one_uid'], 
                                    self.config['one_home'],
                                    self.config['one_password'])
        self.machine.configureONeAdminEnv()
        self.machine.configureONeAdminAuth()
        self.machine.setupONeAdminSSHCred(self.config['one_ssh_key'])

    def installONe(self):
        self.machine.installDependencies()
        self.machine.cloneGitRepository(self.config['one_build_dir'],
                                        self.config['one_git_repo'], 
                                        self.config['one_clone_name'],
                                        self.config['one_branch'])  
        self.machine.buildOpenNebula()
        self.machine.installOpenNebula()
        
    def setupONeEnv(self):
        if self.config['share_type'] == 'nfs':
            self.machine.configureNFS(self.config['network_addr'],
                                      self.config['network_mask'])
        elif self.config['share_type'] == 'ssh':
            self.machine.configureSSH()

    def configureONeD(self):
        if not os.path.isfile(self.ONeDConfTemplateFile):
            raise ValueError('ONe daemon configuration template does '
                'not exists')

        ONeDConfTemplate = fileGetContents(self.ONeDConfTemplateFile)         
        filePutContents('%s/var/oned.conf' % self.config['one_home'],
            ONeDConfTemplate % self.config)

    def startONe(self):
        self.machine.startONeDaemon()

