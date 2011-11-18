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

import string
import os
import re
import socket
from stratuslab.system import SystemFactory
from stratuslab.Util import printStep, printWarning, fileGetContent
import stratuslab.Util as Util
from stratuslab.PersistentDisk import PersistentDisk as PDiskClient
from random import choice
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab import Defaults

class PersistentDisk(object):

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        self.configHolder.assign(self)
        
        self.system = None
        self.profile = None # Can be frontend or node
        
        # Package to be installed
        self.packages = { 'frontend': {
                            'pdisk': ['pdisk-server', ],
                            'iscsi': ['scsi-target-utils', ],
                            'nfs': ['nfs-utils', 'nfs-utils-lib'],
                            'lvm': ['lvm2', ],
                            'file': [], 
                        }, 
                         'node': {
                            'pdisk': ['pdisk-host', ],
                            'iscsi': ['iscsi-initiator-utils', ],
                            'nfs': ['nfs-utils', 'nfs-utils-lib'],
                            'lvm': [],
                            'file': [],
                       },
        }

        self.authnConfigFile = Defaults.AUTHN_CONFIG_FILE
        self.pdiskConfigFile = '/etc/stratuslab/pdisk.cfg'
        self.pdiskHostConfigFile = '/etc/stratuslab/pdisk-host.cfg'
        self.cloudNodeKey = '/opt/stratuslab/storage/pdisk/cloud_node.key'
        self.pdiskUsername = 'pdisk'
        self.pdiskPassword = self._extractPdiskPassword()
        
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
        if not self.persistentDiskIp:
            self.persistentDiskIp = socket.gethostbyname(socket.gethostname())
        
        self.system.setNodeAddr(self.persistentDiskIp)
        self._commonInstallActions()
        self._copyCloudNodeKey()
        self._service('pdisk', 'start')
        
    def configureFrontend(self):
        self._writePdiskConfig()
        self._setAutorunZookeeper()
        self._setPdiskUserAndPassword()
        # self._mergeAuthWithProxy()  ### No longer needed, using common cfg.
        self._service('pdisk', 'restart')
        if self.persistentDiskShare == 'nfs':
            return
        if self.persistentDiskStorage == 'lvm':
            self._createLvmGroup()
            self._fixUdevForLvmMonitoring()
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
        self._configureNodeScripts()
        
    def _configureNodeSudo(self):
        printStep('Configuring sudo rights...')
        self.system._remoteAppendOrReplaceInFile('/etc/sudoers',
             '%s ALL = NOPASSWD: /sbin/iscsiadm, /usr/sbin/lsof, /usr/bin/virsh' % self.oneUsername,
             '%s ALL = NOPASSWD: /sbin/iscsiadm, /usr/sbin/lsof, /usr/bin/virsh' % self.oneUsername)
        self.system._remoteAppendOrReplaceInFile('/etc/sudoers',
             'Defaults:%s !requiretty' % self.oneUsername,
             'Defaults:%s !requiretty' % self.oneUsername)
        
    def _configureNodeScripts(self):
        printStep('Configuring node script...')
        self._overrideValueInFile('SHARE_TYPE', self.persistentDiskShare,
                                  self.pdiskHostConfigFile)
        self._overrideValueInFile('NFS_LOCATION', self.persistentDiskNfsMountPoint,
                                  self.pdiskHostConfigFile)
        self._overrideValueInFile('PDISK_USER', self.pdiskUsername,
                                  self.pdiskHostConfigFile)
        self._overrideValueInFile('PDISK_PSWD', self.pdiskPassword,
                                  self.pdiskHostConfigFile)
        
    def _installPackages(self, section):
        if self.packages:
            printStep('Installing packages on %s for section "%s": %s' 
                      % (self.profile, section, 
                         ', '.join(self.packages[self.profile][section])))
            self.system.installNodePackages(self.packages[self.profile][section])

    def _randomPassword(self, length=12, chars=string.letters+string.digits):
        return ''.join([choice(chars) for i in range(length)])
            
    def _commonInstallActions(self):
        self.system.workOnNode()
        self._installPackages('pdisk')
        self._installPackages(self.persistentDiskShare)
        if self.persistentDiskShare == 'nfs':
            self._configureNfsServer()
        else:
            self._installPackages(self.persistentDiskStorage)
        
    def _service(self, service, action):
        printStep("Trying to %s %s service..." % (action, service))
        self.system._nodeShell('/etc/init.d/%s %s' % (service, action))
        
    def _overrideConfig(self, key, value):
        self._overrideValueInFile(key, value, self.pdiskConfigFile)    
        
    def _overrideValueInFile(self, key, value, fileName):
        search = key + '=.*'
        replace = key + '=' + value
        self.system._remoteAppendOrReplaceInFile(fileName, search, replace)
        
    def _extractPdiskPassword(self):

        pswd = self._randomPassword()
    
        if not os.path.isfile(self.authnConfigFile):
            lines = []
        else:
            fileContent = fileGetContent(self.authnConfigFile)
            lines = fileContent.split('\n')
        
        pattern = '^\s*%s\s*=\s*([\w-]+)(?:\s*,.*)?$' % (self.pdiskUsername)
        search = re.compile(pattern)

        for line in lines:
            if search.match(line):
                pswd = search.findall(line)[0]
            
        return pswd

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
        
    def _copyCloudNodeKey(self):
        self.system.copyCmd(self.persistentDiskCloudNodeKey, self.cloudNodeKey)
        
    def _writePdiskConfig(self):
        printStep('Writing configuration...')
        self._overrideConfig('disk.store.share', self.persistentDiskShare)
        self._overrideConfig('disk.store.nfs.location', self.persistentDiskNfsMountPoint)
        self._overrideConfig('disk.store.iscsi.type', self.persistentDiskStorage)
        self._overrideConfig('disk.store.iscsi.file.location', self.persistentDiskFileLocation)
        self._overrideConfig('disk.store.lvm.device', self.persistentDiskLvmDevice)
        self._overrideConfig('disk.store.lvm.create', self.persistentDiskLvmCreate)
        self._overrideConfig('disk.store.lvm.remove', self.persistentDiskLvmRemove)
        self._overrideConfig('disk.store.zookeeper.address', self.persistentDiskZookeeperAddr)
        self._overrideConfig('disk.store.cloud.node.admin', self.oneUsername)
        self._overrideConfig('disk.store.cloud.node.ssh_keyfile', self.cloudNodeKey)
        self._overrideConfig('disk.store.cloud.node.vm_dir', self.persistentDiskCloudVmDir)
        
    def _setAutorunZookeeper(self):
        # By default script auto run
        if not self.persistentDiskAutorunZookeeper:
            printStep('Setting Zookeeper to run with pdisk...')
            self._overrideValueInFile('persistentDisk', 0, '/etc/init.d/pdisk')

    def _setPdiskUserAndPassword(self):
        self._overrideValueInFile(self.pdiskUsername, 
                                  '%s,cloud-access' % (self.pdiskPassword), 
                                  self.authnConfigFile)
            
    def _mergeAuthWithProxy(self):
        loginConf = '/etc/stratuslab/%s/login.conf'
        pdiskDir = 'storage/pdisk'
        oneproxyDir = 'one-proxy'
        confLine = '<Arg>%s</Arg>'
        configFile = '/opt/stratuslab/storage/pdisk/etc/jetty-jaas-stratuslab.xml'
        if not self.persistentDiskMergeAuthWithProxy:
            return
        printStep('Merging pdisk and one-proxy auth configuration...')
        if not self.system._remoteFileExists(loginConf % oneproxyDir):
            printWarning('Not merging login configuration with one proxy, '
                         'not able to find one-proxy configuration file.\n'
                         'Edit %s to do it.' % loginConf % pdiskDir)
            return
        if 0 == self.system._nodeShell(['grep', '"%s"' % confLine % loginConf % oneproxyDir, configFile]):
            return
        self.system._remoteAppendOrReplaceInFile(
             configFile,
             confLine % loginConf % pdiskDir,
             confLine % loginConf % oneproxyDir)
        
    def _configureNfsServer(self):
        printStep('Configuring NFS sharing...')
        if self._nfsShareAlreadyExists():
            self.system.configureExistingNfsShare(self.persistentDiskExistingNfs, 
                                                  self.persistentDiskNfsMountPoint)
        elif self.profile == 'node':
            self.system.configureExistingNfsShare('%s:%s' % (PDiskClient.getFQNHostname(self.persistentDiskIp), self.persistentDiskNfsMountPoint), 
                                                  self.persistentDiskNfsMountPoint)
        else:
            self.system.configureNewNfsServer(self.persistentDiskNfsMountPoint,
                                              self.networkAddr,
                                              self.networkMask)

    def _nfsShareAlreadyExists(self):
        return not (self.persistentDiskExistingNfs == '')

    def _fixUdevForLvmMonitoring(self):
        """See the issue: https://bugzilla.redhat.com/show_bug.cgi?id=577798#c5
        1. Modify 80-udisks.rules
        2. Install a cron job to modify 80-udisks.rules file to safeguard against
           udev package updates.
        """
        fileName = '/lib/udev/rules.d/80-udisks.rules'

        if not os.path.exists(fileName):
            return

        search = 'KERNEL=="dm-*", OPTIONS+="watch"'
        replace = '#KERNEL=="dm-*", OPTIONS+="watch"'
        if re.search('^KERNEL=="dm-\*", OPTIONS\+="watch"', Util.fileGetContent(fileName), re.MULTILINE):
            Util.appendOrReplaceInFile(fileName, search, replace)

        #self.system.restartService('udev')

        data = """*/15 * * * * root sed -i -e 's/^KERNEL==\"dm-\*\", OPTIONS+=\"watch\"/%s/' %s""" % \
                (replace, fileName)
        Util.filePutContent('/etc/cron.d/fix-udev-for-lvm-monitoring.cron', data)
