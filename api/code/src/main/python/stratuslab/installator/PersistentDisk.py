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

import os
import re
import socket
import string
import stat
from random import choice

import stratuslab.Util as Util
from stratuslab import Defaults
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Util import printStep, fileGetContent
from stratuslab.system import SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab.Exceptions import ExecutionException
from stratuslab.volume_manager.volume_manager import VolumeManager


class PersistentDisk(Installator):
    PDISK_BACKEND_CONF_NAME = 'pdisk-backend.cfg'
    pdiskConfigBackendFile = os.path.join(Defaults.ETC_DIR, PDISK_BACKEND_CONF_NAME)
    PDISK_DB_NAME = 'storage'

    def __init__(self, configHolder=ConfigHolder()):
        self.persistentDiskDbHost = 'localhost'

        self.configHolder = configHolder
        self.configHolder.assign(self)

        self.profile = None # Can be frontend or node
        self.system = SystemFactory.getSystem(self.persistentDiskSystem,
                                              self.configHolder)

        # Package to be installed
        self.packages = {'frontend': {
            'pdisk': ['stratuslab-pdisk-server', ],
            'iscsi': ['scsi-target-utils', 'iscsi-initiator-utils'],
            'nfs': ['nfs-utils', 'nfs-utils-lib'],
            'lvm': ['lvm2', ],
            'file': ['qemu-img'],
        },
                         'node': {
                             'pdisk': ['stratuslab-pdisk-host', ],
                             'iscsi': ['iscsi-initiator-utils', ],
                             'nfs': ['nfs-utils', 'nfs-utils-lib'],
                             'lvm': [],
                             'file': [],
                         },
        }

        self.pdiskConfigBackendTpl = Util.get_template_file([self.PDISK_BACKEND_CONF_NAME + '.tpl'])
        self.authnConfigFile = Defaults.AUTHN_CONFIG_FILE
        self.pdiskConfigFile = os.path.join(Defaults.ETC_DIR, 'pdisk.cfg')
        self.pdiskHostConfigFile2 = os.path.join(Defaults.ETC_DIR, 'pdisk-host.conf')
        self.pdiskHomeDir = '/opt/stratuslab/storage/pdisk'
        self.cloudNodeKey = os.path.join(self.pdiskHomeDir, 'cloud_node.key')
        self.pdiskUsername = 'pdisk'
        self.pdiskPassword = self._extractPdiskPassword()

    def _setPDiskEndpoint(self):
        '''Fool the script to avoid rewrite huge amount of code:
           As the pdisk service can be installed on another machine than the
           frontend, we need to do an installation via SSH like for node.
        '''
        self.system.setNodePrivateKey(self.persistentDiskPrivateKey)
        if not self.persistentDiskIp:
            self.persistentDiskIp = socket.gethostbyname(socket.gethostname())

        self.system.setNodeAddr(self.persistentDiskIp)

    def _installFrontend(self):
        self._setPDiskEndpoint()
        self.profile = 'frontend'
        self._validateConfiguration()
        self._commonInstallActions()
        self._copyCloudNodeKey()

    def _validateConfiguration(self):
        pass

    def _setupFrontend(self):
        self._setPDiskEndpoint()
        self._writePdiskConfig()
        self._writePdiskBackendConfig()
        self._setPdiskUserAndPassword()
        # downloading images requires configured client on front-end
        self._updateConfigHostPDiskClient()
        self._createDatabase()
        if self.persistentDiskShare == 'nfs':
            return
        if self.persistentDiskStorage == 'lvm':
            self._writeTgtdConfig()
            self._createLvmGroup()
            self._fixUdevForLvmMonitoring()
        else:
            self._createFileHddDirectory()


    def _writePdiskConfig(self):
        printStep('Writing configuration...')
        self._overrideConfig('disk.store.share', self.persistentDiskShare)
        self._overrideConfig('disk.store.nfs.location', self.persistentDiskNfsMountPoint)
        self._overrideConfig('disk.store.iscsi.type', self.persistentDiskStorage)
        self._overrideConfig('disk.store.iscsi.file.location', self.persistentDiskFileLocation)
        self._overrideConfig('disk.store.lvm.device', self.persistentDiskLvmDevice)
        self._overrideConfig('disk.store.lvm.create', self.persistentDiskLvmCreate)
        self._overrideConfig('disk.store.lvm.remove', self.persistentDiskLvmRemove)
        self._overrideConfig('disk.store.cloud.node.admin', self.oneUsername)
        self._overrideConfig('disk.store.cloud.node.ssh_keyfile', self.cloudNodeKey)
        self._overrideConfig('disk.store.cloud.node.vm_dir', self.persistentDiskCloudVmDir)

    def _writePdiskBackendConfig(self):
        printStep('Writing backend configuration...')
        config = self.__dict__.copy()
        config['persistentDiskBackendSections'] = self._stripMultiLineValue(config['persistentDiskBackendSections'])
        self.system._remoteFilePutContents(self.pdiskConfigBackendFile,
                                           fileGetContent(self.pdiskConfigBackendTpl) % config)

    def _writeTgtdConfig(self):
        iscsi_config_filename = os.path.join(Defaults.ETC_DIR, 'iscsi.conf')

        if not os.path.exists(iscsi_config_filename):
            with open(iscsi_config_filename, 'w') as config:
                config.write(' ')

        pattern = 'include %s' % iscsi_config_filename
        Util.appendOrReplaceInFile('/etc/tgt/targets.conf', pattern, pattern)

    def _createDatabase(self):
        """Create DB only if RDMS is on the same host."""
        if not self._isDbOnPdiskHost():
            return

        mysqlCommand = "/usr/bin/mysql -uroot -p%s" % self.oneDbRootPassword
        createDbIfNotExist = "CREATE DATABASE IF NOT EXISTS %s" % PersistentDisk.PDISK_DB_NAME

        rc, output = self.system.execute("%s -e \"%s\"" % (mysqlCommand, createDbIfNotExist),
                                         withOutput=True, shell=True)
        if rc != 0:
            raise ExecutionException("Couldn't create database '%s'.\n%s" % (PersistentDisk.PDISK_DB_NAME,
                                                                             output))

    def _isDbOnPdiskHost(self):
        return self.persistentDiskDbHost in ['localhost', '127.0.0.1',
                                             self.persistentDiskIp,
                                             VolumeManager.getFQNHostname(self.persistentDiskIp)]

    def _startServicesFrontend(self):
        self._setPDiskEndpoint()
        if self.persistentDiskStorage == 'lvm':
            self._startService('tgtd')
        self._startService('pdisk')

    def _startService(self, service):
        try:
            self._service(service, 'stop')
        except:
            pass # it's ok
        self._service(service, 'start')

    def _installNode(self):
        self.profile = 'node'
        self._commonInstallActions()

    def _setupNode(self):
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
        self.system._remoteAppendOrReplaceInFile('/etc/sudoers',
                                                 'Defaults:%s !requiretty' % 'root',
                                                 'Defaults:%s !requiretty' % 'root')

    def _configureNodeScripts(self):
        printStep('Configuring node script...')

        self._updateConfigHostPDiskClient()

    def _updateConfigHostPDiskClient(self):
        self._overrideHostConfigFile2('pdisk_user', self.pdiskUsername)
        self._overrideHostConfigFile2('pdisk_passwd', self.pdiskPassword)

        self.system._remoteCreateDirs(self.persistentDiskHostVolumeMgmtDir)
        perm_1757 = stat.S_ISVTX | stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IRWXO
        self.system._remoteChmod(self.persistentDiskHostVolumeMgmtDir, perm_1757)
        self._overrideHostConfigFile2('volume_mgmt_dir', self.persistentDiskHostVolumeMgmtDir)

    def _installPackages(self, section):
        packages = self.packages[self.profile].get(section, [])
        if packages:
            printStep('Installing packages on %s for section "%s": %s'
                      % (self.profile, section,
                         ', '.join(packages)))
            self.system.installNodePackages(packages)

    def _randomPassword(self, length=12, chars=string.letters + string.digits):
        return ''.join([choice(chars) for _ in range(length)])

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
        self.system._nodeShell('service %s %s' % (service, action))

    def _overrideConfig(self, key, value):
        self._overrideValueInFile(key, value, self.pdiskConfigFile)

    def _overrideHostConfigFile2(self, key, value):
        self._overrideValueInFile(key, value, self.pdiskHostConfigFile2)

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
                               % (self.persistentDiskLvmPvcreate, self.persistentDiskPhysicalDevices))
        self.system._nodeShell('%s %s %s'
                               % (self.persistentDiskLvmVgcreate, self.persistentDiskLvmDevice,
                                  self.persistentDiskPhysicalDevices))

    def _createFileHddDirectory(self):
        printStep('Creating disk store directory...')
        self.system._remoteCreateDirs(self.persistentDiskFileLocation)

    def _copyCloudNodeKey(self):
        self.system.copyCmd(self.persistentDiskCloudNodeKey, self.cloudNodeKey)

    def _stripMultiLineValue(self, value):
        return '\n'.join(map(lambda x: x.strip(), value.split('\n')))

    def _setPdiskUserAndPassword(self):
        self._overrideValueInFile(self.pdiskUsername,
                                  '%s,cloud-access' % (self.pdiskPassword),
                                  self.authnConfigFile)

    def _mergeAuthWithProxy(self):
        loginConf = os.path.join(Defaults.ETC_DIR, '%s/login.conf')
        pdiskDir = 'storage/pdisk'
        oneproxyDir = 'one-proxy'
        confLine = '<Arg>%s</Arg>'
        configFile = os.path.join(self.pdiskHomeDir, 'etc/jetty-jaas-stratuslab.xml')
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
            self.system.configureExistingNfsShare('%s:%s' % (
            VolumeManager.getFQNHostname(self.persistentDiskIp), self.persistentDiskNfsMountPoint),
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
