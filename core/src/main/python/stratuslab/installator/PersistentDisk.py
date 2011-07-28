#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Centre National de la Recherche Scientifique (CNRS)
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

from stratuslab.system import SystemFactory
from stratuslab.Util import printStep, printWarning

class PersistentDisk(object):

    def __init__(self, configHolder):
        self.configHolder = configHolder
        self.configHolder.assign(self)
        
        self.system = None
        self.profile = None # Can be frontend or node
        
        # Package to be installed
        self.packages = { 'frontend': {
                            'pdisk': ['pdisk-server', ],
                            'iscsi': ['scsi-target-utils', ],
#                            'nfs': [],
                            'lvm': ['lvm2', ],
                            'file': [], 
                        }, 
                         'node': {
                            'pdisk': ['pdisk-host', ],
                            'iscsi': ['iscsi-initiator-utils', ],
#                            'nfs': [],
                            'lvm': [],
                            'file': [],
                       },
        }
        # Services to be started on frontend
        self.services = { 'pdisk': 'pdisk-server',
                          'iscsi': 'tgtd',
#                          'nfs': '', 
        } 

        self.pdiskConfigFile = '/etc/stratuslab/pdisk.cfg'
        
    def runFrontend(self):
        self.installFrontend()
        self.configureFrontend()

    def installFrontend(self):
        self.profile = 'frontend'
        self.system = SystemFactory.getSystem(self.persistentDiskSystem, self.configHolder)
        # Fool the script to avoid rewrite huge amount of code:
        # As the pdisk service can be installed on another machine than the
        # frontend, we need to do an installation via SSH like for node.
        self.system.setNodePrivateKey(self.persistentDiskPrivateKey)
        self.system.setNodeAddr(self.persistentDiskIp)
        self._commonInstallActions()
        self._service('pdisk', 'start')
        
    def configureFrontend(self):
        self._writeConfig()
        self._setAutorunZookeeper()
        self._mergeAuthWithProxy()
        self._service('pdisk', 'restart')
        if self.persistentDiskStorage == 'lvm':
            self._createLvmGroup()
        else:
            self._createFileHddDirectory()
    
    def runNode(self):
        self.installNode()
        self.configureNode()
    
    def installNode(self):
        self.profile = 'node'
        self.system = SystemFactory.getSystem(self.nodeSystem, self.configHolder)
        self._commonInstallActions()
        
    def configureNode(self):
        self._configureNodeSudo()
        
    def _configureNodeSudo(self):
        self.system._remoteAppendOrReplaceInFile('/etc/sudoers',
             '%s ALL = NOPASSWD: /sbin/iscsiadm' % self.oneUsername,
             '%s ALL = NOPASSWD: /sbin/iscsiadm' % self.oneUsername)
        
    def _installPackages(self, section):
        if self.packages:
            printStep('Installing packages on %s for section "%s": %s' 
                      % (self.profile, section, 
                         ', '.join(self.packages[self.profile][section])))
            self.system.installNodePackages(self.packages[self.profile][section])
            
    def _commonInstallActions(self):
        self._installPackages('pdisk')
        self._installPackages(self.persistentDiskShare)
        self._installPackages(self.persistentDiskStorage)
        
    def _service(self, service, action):
        printStep("Trying to %s %s service..." % (action, service))
        self.system._nodeShell('/etc/init.d/%s %s' % (service, action), pseudoTTY=True)
        
    def _overrideConfig(self, key, value):
        self._overrideValueInFile(key, value, self.pdiskConfigFile)    
        
    def _overrideValueInFile(self, key, value, fileName):
        search = key + '=.*'
        replace = key + '=' + value
        self.system._remoteAppendOrReplaceInFile(fileName, search, replace)
        
    def _createLvmGroup(self):
        if 0 == self.system._nodeShell('%s %s' 
              % (self.persistentDiskLvmVgdisplay, self.persistentDiskLvmDevice)):
            return
        printStep('Creating LVM volume group...')
        self.system._nodeShell('%s %s' 
           % (self.persistentDiskLvmPvcreate, self.persistentDiskPhysicalDevice))
        self.system._nodeShell('%s %s' 
           % (self.persistentDiskLvmVgcreate, self.persistentDiskLvmDevice))
                
    def _createFileHddDirectory(self):
        printStep('Creating disk store directory...')
        self.system._remoteCreateDirs(self.persistentDiskFileLocation)
        
    def _writeConfig(self):
        printStep('Writting configuration...')
        self._overrideConfig('disk.store.type', self.persistentDiskStorage)
        self._overrideConfig('disk.store.share', self.persistentDiskShare)
        self._overrideConfig('disk.store.file.location', self.persistentDiskFileLocation)
        self._overrideConfig('disk.store.lvm.device', self.persistentDiskLvmDevice)
        self._overrideConfig('disk.store.lvm.create', self.persistentDiskLvmCreate)
        self._overrideConfig('disk.store.lvm.remove', self.persistentDiskLvmRemove)
        self._overrideConfig('disk.store.zookeeper.address', self.persistentDiskZookeeperAddr)
        self._overrideConfig('disk.store.zookeeper.port', self.persistentDiskZookeeperPort)
        
    def _setAutorunZookeeper(self):
        # By default script auto run
        if not self.persistentDiskAutorunZookeeper:
            printStep('Setting Zookeeper to run with pdisk...')
            self._overrideValueInFile('persistentDisk', 0, '/etc/init.d/pdisk')
            
    def _mergeAuthWithProxy(self):
        loginConf = '/etc/stratuslab/%s/login.conf'
        pdiskDir = 'storage/pdisk'
        oneproxyDir = 'one-proxy'
        confLine = '<Arg>%s</Arg>'
        configFile = '/opt/stratuslab/storage/pdisk/etc/jetty-jaas-stratuslab.xml'
        if not self.persistentDiskMergeAuthWithProxy:
            return
        if not self.system._remoteFileExists(loginConf % oneproxyDir):
            printWarning('Not merging login configuration with one proxy, '
                         'not able to find one-proxy configuration file.\n'
                         'Edit %s to do it.' % loginConf % pdiskDir)
            return
        if 0 == self.system._nodeShell(['grep', '"%s"' % confLine % loginConf % oneproxyDir, configFile]):
            return
        printStep('Merging pdisk and one-proxy auth configuration...')
        self.system._remoteAppendOrReplaceInFile(
             configFile,
             confLine % loginConf % pdiskDir,
             confLine % loginConf % oneproxyDir)
            
            
            