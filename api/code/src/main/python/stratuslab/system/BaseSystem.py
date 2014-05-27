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
import re
import shutil
import time
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from stratuslab import Exceptions
from stratuslab import Defaults
from stratuslab.Util import appendOrReplaceInFile, execute, fileAppendContent, \
    fileGetContent, filePutContent, scp, sshCmd
import stratuslab.Util as Util
from stratuslab.system.PackageInfo import PackageInfo
from stratuslab.system import Systems
from stratuslab.Exceptions import ExecutionException


class BaseSystem(object):

    os = ''
    caRepoName = 'CAs'
    voIdCardUrl = 'http://operations-portal.egi.eu/xml/voIDCard/public/all/true'
    vomsesDir = '/etc/grid-security/vomsdir'

    def __init__(self):
        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        tmpdir = tempfile.gettempdir()
        self.stdout = open(os.path.join(tmpdir,('stratuslab_%s.log' % dateNow)), 'a')
        self.stderr = open(os.path.join(tmpdir,('stratuslab_%s.err' % dateNow)), 'a')

        self.extraRepos = {}
        self.packages = {}
        self.packages.update({'opennebula' : PackageInfo('one-3.2-StratusLab')})
        self.installPackagesErrorMsgs = []
        self.repoFileNamePattern = '/etc/%s'
        self.certificateAuthorityPackages = ''
        self.certificateAuthorityRepo = ''

        self.workOnFrontend()
        self.oneDbUsername = None
        self.oneDbPassword = None

        self.qemuConf = '/etc/libvirt/qemu.conf'

        self.shareType = Defaults.SHARE_TYPE

    def init(self):
        self._setOneHome()

    # -------------------------------------------
    #     Packages manager and related
    # -------------------------------------------

    def addRepositories(self, packages):
        pass

    def updatePackageManager(self):
        pass

    def installWebServer(self):
        pass

    def installPackages(self, packages):
        if len(packages) < 1:
            return

        self.addRepositories(packages)

        packages_versioned = []
        for package in packages:
            packages_versioned.append(
                            self.getPackageWithVersionForInstall(package))

        cmd = '%s %s' % (self.installCmd, ' '.join(packages_versioned))
        rc, output = self._executeWithOutput(cmd, shell=True)
        if rc != 0:
            raise ExecutionException('Failed to install: %s\n%s' % \
                                     (', '.join(packages_versioned), output))

        Util.printDetail(output, self.verboseLevel, Util.VERBOSE_LEVEL_DETAILED)

    def getPackageWithVersionForInstall(self, package):
        try:
            self.packages[package]
        except KeyError:
            return package
        else:
            if self.packages[package].packageVersion:
                return '%s%s%s*' % (self.packages[package].packageName,
                                    self._getPackageAndVersionSeparator(),
                                    self.packages[package].packageVersion)
            else:
                return self.packages[package].packageName

    def _getPackageAndVersionSeparator(self):
        return Systems.getPackageAndVersionSeparatorBasedOnOs(self.os)


    def installNodePackages(self, packages):
        if len(packages) > 0:
            rc, output = self._nodeShell('%s %s' %
                                     (self.installCmd, ' '.join(packages)),
                                     withOutput=True)
            if rc != 0:
                raise Exceptions.ExecutionException('Error installing packages: %s\n%s' % \
                                         (packages, output))
            for err in self.installPackagesErrorMsgs:
                if re.search(err, output, re.M):
                    raise Exceptions.ExecutionException('Error installing packages: %s\n%s' % \
                                             (packages, output))

    def installFrontendDependencies(self):
        self.addRepositories(self.frontendDeps)
        self.updatePackageManager()
        self.installPackages(self.frontendDeps)

    def installNodeDependencies(self):
        self.installNodePackages(self.nodeDeps)

    def installHypervisor(self):
        self.installNodePackages(self.hypervisorDeps.get(self.hypervisor))


    def _updatePackageAndRepoInfo(self, packageName, repoName, repoConf):
        self.packages[packageName] = PackageInfo(packageName, repository=repoName)
        self.extraRepos[repoName] = {'content' : repoConf,
                                     'filename' : self.repoFileNamePattern % repoName}

    def getPackageName(self, package):
        return self.packages[package].packageName

    def getPackageConfigFileName(self, package):
        return self.packages[package].configFile

    def getPackageInitdScriptName(self, package):
        return self.packages[package].initdScriptName

    def getPakcageRepositoryName(self, package):
        return self.packages[package].repository

    def getPakcageRepositoryConfig(self, package):
        repoName = self.getPakcageRepositoryName(package)
        return self.extraRepos[repoName]

    def getIsPackageInstalledCommand(self, package):
        pass

    def isPackageInstalled(self, package):
        cmd = self.getIsPackageInstalledCommand(package)

        rc, output = self._executeWithOutput(cmd, shell=True)

        if rc != 0:
            Util.printDetail(output)
            return False

        return True

    def startService(self, service):
        return self._operationOnService(service, 'start')

    def stopService(self, service):
        return self._operationOnService(service, 'stop')

    def restartService(self, service):
        return self._operationOnService(service, 'restart')

    def _operationOnService(self, service, operation):
        cmd = ['service', service, operation]
        rc, output = self._executeWithOutput(cmd)
        if rc != 0:
            Util.printDetail(output)
        return rc

    def startCloudSystem(self):
        self.stopService('oned')
        if self.startService('oned'):
            Util.printError("ONE failed to start")
        Util.printDetail('Waiting for ONE to finish starting')
        time.sleep(10)

    def enableServiceOnBoot(self, service, level='3'):
        return 0

    # -------------------------------------------
    #     ONE admin creation
    # -------------------------------------------

    def createCloudGroup(self, groupname, gid):
        self.oneGroup = groupname
        self.oneGid = gid

        self.executeCmd(['groupadd', '-g', self.oneGid,
                        self.oneGroup])

    def createCloudAdmin(self):
        # see below...
        # self.createDirsCmd(os.path.dirname(self.oneHome))

        self.executeCmd(['useradd', '-g',
                        self.oneGroup, '-u', self.oneUid, self.oneUsername,
                        '-s', '/bin/bash', '-p', self.onePassword, '--create-home',
                        '--expiredate ""', '--inactive -1'])

        # hack to reset the value of self.oneHome
        # the code assumes that the account exists before initializing this class
        # this is not the case as it is created by installing the one package
        self.oneHome = None
        self._setOneHome()

    # -------------------------------------------
    #     ONE admin env config and related
    # -------------------------------------------

    def configureCloudAdminEnv(self, ONeDPort, stratuslabLocation):
        self.ONeDPort = ONeDPort

        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                      'export ONE_LOCATION',
                                      'export ONE_LOCATION=%s' % self.oneHome)
        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                      'export ONE_XMLRPC',
                                      'export ONE_XMLRPC=http://localhost:%s/RPC2' % self.ONeDPort)
        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                      'export PATH',
                                      'export PATH=%s/bin:%s' % (self.oneHome, os.getenv('PATH')))

        if stratuslabLocation:
            self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                          'export STRATUSLAB_LOCATION',
                                          'export STRATUSLAB_LOCATION=%s' % stratuslabLocation)

        self.filePutContentsCmd('%s/.bash_login' % self.oneHome,
                                '[ -f ~/.bashrc ] && source ~/.bashrc')
        self.setOwnerCmd('%s/.bash_login' % self.oneHome)

        # Hack to always load .bashrc
        self.executeCmd(['sed -i \'s/\[ -z \\\"\$PS1\\\" \\] \\&\\& '
                        'return/#&/\' %s/.bashrc' % self.oneHome], shell=True)

    def configureCloudAdminSshKeys(self):
        keyFileName = '%s/.ssh/id_rsa' % self.oneHome

        if os.path.exists(keyFileName):
            Util.printDetail('Key file %s already exists, skipping this step' % keyFileName)
            return

        self.createDirsCmd(os.path.dirname(keyFileName))
        self.setOwnerCmd(os.path.dirname(keyFileName))
        self.executeCmd(['ssh-keygen -f %s -N "" -q' % keyFileName],
                        shell=True)
        self.setOwnerCmd(keyFileName)
        self.setOwnerCmd('%s.pub' % keyFileName)

        self.copyCmd('%s.pub' % keyFileName,
                     '%s/.ssh/authorized_keys' % self.oneHome)
        self.setOwnerCmd('%s/.ssh/authorized_keys' % self.oneHome)
        self._configureCloudAdminSsh()

    def configureCloudAdminSshKeysNode(self):

        self.createDirsCmd('%s/.ssh/' % self.oneHome)
        self.setOwnerCmd('%s/.ssh/' % self.oneHome)

        # FIXME: why ssh key-pair from the Frontend is pushed to the Node?
        #        ssh-keygen on the Node should be used to generate the user
        #        specific ssh key-pair on that machine.
        oneKey = fileGetContent('%s/.ssh/id_rsa' % self.oneHome)
        self._filePutContentAsOneAdmin('%s/.ssh/id_rsa' % self.oneHome, oneKey)

        oneKeyPub = fileGetContent('%s/.ssh/id_rsa.pub' % self.oneHome)
        self._filePutContentAsOneAdmin('%s/.ssh/authorized_keys' % self.oneHome,
                                       oneKeyPub)
        self.chmodCmd('%s/.ssh/id_rsa' % self.oneHome, 0600)

        self._configureCloudAdminSsh()

    def _configureCloudAdminSsh(self):
        confFile = '%s/.ssh/config' % self.oneHome

        self.appendOrReplaceInFileCmd(confFile,
                                      '^Host.*$', 'Host *')
        self.appendOrReplaceInFileCmd(confFile,
                                      '^StrictHost.*$', 'StrictHostKeyChecking no')
        self.setOwnerCmd(confFile)
        self.chmodCmd(confFile, 0600)

    def configureCloudAdminAccount(self):
        # hack to reset the value of self.oneHome
        # the code assumes that the account exists before initializing this class
        # this is not the case as it is created by installing the one package
        self.oneHome = None
        self._setOneHome()

        oneAuthFile = '%s/.one/one_auth' % self.oneHome
        self.appendOrReplaceInFileCmd(oneAuthFile,
                                      self.oneUsername, '%s:%s' % (self.oneUsername, self.onePassword))
        os.environ['ONE_AUTH'] = oneAuthFile

        self.addCloudAdminToExtraGroups()

        self.configureCloudAdminSudoFrontend()

    def addCloudAdminToExtraGroups(self):
        if Util.isTrueConfVal(self.persistentDisk) and self.persistentDiskStorage == 'lvm':
            self._addCloudAdminToExtraGroup(self.persistentDiskLvmDevfilesGroup)

    def _addCloudAdminToExtraGroup(self, group):
            self.executeCmd(['usermod', '-aG', group, self.oneUsername])

    def configureCloudAdminSudoFrontend(self):
        commands = ['/sbin/lvs',
                    '/var/lib/stratuslab/python/stratuslab/tm/TMMakeVFAT.py']
        self._configureCloudAdminSudo(commands)

    def configureCloudAdminSudoNode(self):
        commands = ['/bin/chmod']
        self._configureCloudAdminSudo(commands)

    def _configureCloudAdminSudo(self, commands):
        Util.printDetail("Configuring sudo rights for '%s'" % self.oneUsername)
        for cmd in commands:
            replace = '%s ALL = NOPASSWD: %s' % (self.oneUsername, cmd)
            self.appendOrReplaceInFileCmd('/etc/sudoers', '%s' % replace, replace)

        replace = 'Defaults:%s !requiretty' % self.oneUsername
        self.appendOrReplaceInFileCmd('/etc/sudoers', '%s' % replace, replace)

        replace = 'Defaults:%s !requiretty' % 'root'
        self.appendOrReplaceInFileCmd('/etc/sudoers', '%s' % replace, replace)

    def _setOneHome(self):
        if not self.oneHome:
            self.oneHome = os.path.expanduser('~' + self.oneUsername)

    # -------------------------------------------
    #     Persistent disks
    # -------------------------------------------

    def configureCloudAdminPdiskNode(self):
        pdiskAttach = '/usr/sbin/attach-persistent-disk.sh'
        pdiskDetach = '/usr/sbin/detach-persistent-disk.sh'

        if Util.isFalseConfVal(getattr(self, 'persistentDisks', False)):
            self.executeCmd('"[ -f %(pd)s ] || { touch %(pd)s; chmod +x %(pd)s; }"' %
                            {'pd':pdiskDetach}, shell=True)
            return

        Util.printDetail("Configuring persistent disks management for "
                         "'%s' user." % self.oneUsername)

        line = 'oneadmin ALL = NOPASSWD: %s, %s' % (pdiskAttach, pdiskDetach)
        self.appendOrReplaceInFileCmd('/etc/sudoers',
                                      '^%s.*persistent-disk.*$' %
                                      self.oneUsername, line)

    # -------------------------------------------
    #     File sharing configuration
    # -------------------------------------------

    def configureNewNfsServer(self, mountPoint, networkAddr, networkMask):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/exports', '%s .*' % mountPoint,
                                      '%s %s/%s(rw,async,no_subtree_check,no_root_squash)' %
                                      (mountPoint, networkAddr, networkMask))
        self.executeCmd(['exportfs', '-a'])

    def configureExistingNfsShare(self, shareLocation, mountPoint):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/fstab', '%s .*' % shareLocation,
                                      '%s %s nfs soft,intr,rsize=32768,wsize=32768,rw 0 0' % (
                                      shareLocation, mountPoint))
        self.executeCmd(['mount', '-a'])

    def configureSshServer(self):
        pass

    def configureSshClient(self, sharedDir):
        self.createDirsCmd(sharedDir)
        self.setOwnerCmd(sharedDir)

    # -------------------------------------------
    #     Hypervisor configuration
    # -------------------------------------------

    def configureHypervisor(self):
        if self.hypervisor == 'xen':
            self._configureXen()
        elif self.hypervisor == 'kvm':
            self._configureKvm()

    def _configureKvm(self):
        self.executeCmd(['modprobe', 'kvm_intel'])
        self.executeCmd(['modprobe', 'kvm_amd'])

        # seen a case when permission of /dev/kvm were 0600
        self.executeCmd(['chmod', '0666', '/dev/kvm'])

        if self.shareType == 'nfs':
                self._configureQemuUserOnFrontend()

    def _configureQemuUserOnFrontend(self):
        """Add qemu user on Fronted with the same UID and GID as on the node
        being configured. Add qemu user to 'cloud' group both on Frontend
        and the node.
        """
        if self.shareType != 'nfs':
                return


        user = group = 'qemu'
        getUidGidCmd = "getent passwd %s"

        Util.printDetail("Configuring '%s' user on Frontend as shared filesystem setup requested." % user)

        def getUidGidFromNode(user):
            rc, output = self._nodeShell(getUidGidCmd % user,
                                         withOutput=True)
            if rc != 0:
                Util.printError("Error getting '%s' user UID/GID from Node.\n%s" %
                                    (user,output))

            return _extractUidGidFromGetentPasswdOutput(output)
        def _extractUidGidFromGetentPasswdOutput(output):
            uid, gid = output.split(':')[2:4] # uid, gid
            if not all([uid, gid]):
                Util.printError("Error extracting '%s' user UID/GID from output.\n%s" %
                                    (user,output))
            return uid, gid

        uidNode, gidNode = getUidGidFromNode(user)

        rc, output = self._executeWithOutput((getUidGidCmd % uidNode).split())
        if rc == 0:
            uidLocal, gidLocal = _extractUidGidFromGetentPasswdOutput(output)
            Util.printDetail("User with UID:%s/GID:%s already configured on Frontend." %
                             (uidLocal, gidLocal), verboseLevel=self.verboseLevel)

            if gidNode != gidLocal:
                Util.printError("Frontend user '%s' GID:%s doesn't match GID:%s on Node %s." %
                                 (gidLocal, user, gidNode, self.nodeAddr))
        else:
            self._execute(['groupadd', '-g', gidNode, '-r', group])
            self._execute(['useradd', '-r', '-u', uidNode, '-g', group,
                             '-d', '/', '-s', '/sbin/nologin',
                             '-c', '"%s user"'%user, user])

        # Instruct libvirt to run VMs with GID of ONE group.
        self.appendOrReplaceInFileCmd(self.qemuConf, '^group.*$',
                                      'group = "%s"' % self.oneGroup)

        # TODO: check why this didn't work
#        # Add the user to ONE admin group. Directory with the images on
#        # shared Frontend is restricted to ONE admin user.
#        cmd = ['usermod', '-aG', self.oneGroup, user]
#        self._execute(cmd)
#        self._nodeShell(cmd)

    def _configureXen(self):
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.oneUsername,
                                      '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xm *' % self.oneUsername)
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.oneUsername,
                                      '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xentop *' % self.oneUsername)
        self.executeCmd(['sed -i -E \'s/Defaults[[:space:]]+requiretty/#&/\''
                        ' /etc/sudoers'])

    def configureLibvirt(self):
        libvirtConf = '/etc/libvirt/libvirtd.conf'

        self.appendOrReplaceInFileCmd(libvirtConf, '^unix_sock_group.*$',
                                      'unix_sock_group = "cloud"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^unix_sock_ro_perms.*$',
                                      'unix_sock_ro_perms = "0777"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^unix_sock_rw_perms.*$',
                                      'unix_sock_rw_perms = "0770"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^auth_unix_ro.*$',
                                      'auth_unix_ro = "none"')
        self.appendOrReplaceInFileCmd(libvirtConf, '^auth_unix_rw.*$',
                                      'auth_unix_rw = "none"')
        self.appendOrReplaceInFileCmd(self.qemuConf, '^vnc_listen.*$',
                                      'vnc_listen = "0.0.0.0"')

    def startLibvirt(self):
        rc, output = self.executeCmd('service libvirtd restart'.split(),
                                     withOutput=True)
        if rc != 0:
            Util.printError('Could not start libvirt.\n%s' % output)

    # -------------------------------------------
    #     Front-end related methods
    # -------------------------------------------

    def execute(self, commandAndArgsList, **kwargs):
        return self._execute(commandAndArgsList, **kwargs)

    def _execute(self, commandAndArgsList, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        return execute(commandAndArgsList,
                       stdout=stdout,
                       stderr=stderr,
                       verboseLevel=self.verboseLevel,
                       verboseThreshold=Util.VERBOSE_LEVEL_DETAILED,
                       **kwargs)

    def _executeWithOutput(self, command, **kwargs):
        kwargs['withOutput'] = True
        return self._execute(command, **kwargs)

    def _setCloudAdminOwner(self, path):
        os.chown(path, int(self.oneUid), int(self.oneGid))

    def _createDirs(self, path):
        if not os.path.isdir(path) and not os.path.isfile(path):
            os.makedirs(path)

    def _copy(self, src, dst):
        if os.path.isfile(src):
            shutil.copy(src, dst)
        else:
            shutil.copytree(src, dst)

    def _remove(self, path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)

    # -------------------------------------------
    #     Node related methods
    # -------------------------------------------

    def _nodeShell(self, command, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        if isinstance(command, list):
            command = ' '.join(command)

        return sshCmd(command,
                      self.nodeAddr,
                      sshKey=self.nodePrivateKey,
                      stdout=stdout,
                      stderr=stderr,
                      verboseLevel=self.verboseLevel,
                      verboseThreshold=Util.VERBOSE_LEVEL_DETAILED,
                      **kwargs)

    def _nodeCopy(self, source, dest, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        return scp(source,
                   'root@%s:%s' % (self.nodeAddr, dest),
                   self.nodePrivateKey,
                   stdout=stdout,
                   stderr=stderr,
                   verboseLevel=self.verboseLevel,
                   verboseThreshold=Util.VERBOSE_LEVEL_DETAILED,
                   **kwargs)

    def _remoteSetCloudAdminOwner(self, path):
        self._nodeShell(['chown %s:%s %s' % (self.oneUid,
                        self.oneGid, path)])

    def _remoteCreateDirs(self, path):
        self._nodeShell('mkdir -p %s' % path)

    def _remoteAppendOrReplaceInFile(self, filename, search, replace):
        res = self._nodeShell(['grep', '"%s"'%search, filename])

        replace = Util.escapeDoubleQuotes(replace)

        if self._patternExists(res):
            rc, output = self._nodeShell('"sed -i \'s|%s|%s|\' %s"' % (search, replace, filename),
                                         withOutput=True, shell=True)
            if rc != 0:
                Util.printError("Failed to modify %s.\n%s" % (filename, output))
        else:
            self._remoteFileAppendContents(filename, replace)

    def _patternExists(self, returnCode):
        return returnCode == 0

    def _remoteCopyFile(self, src, dest):
        self._nodeShell(['cp -rf %s %s' % (src, dest)])

    def _remoteRemove(self, path):
        self._nodeShell(['rm -rf %s' % path])

    def _remoteFilePutContents(self, filename, data):
        data = Util.escapeDoubleQuotes(data, times=4)

        rc, output = self._nodeShell('"echo \\"%s\\" > %s"' % (data, filename),
                                     withOutput=True, shell=True)
        if rc != 0:
            Util.printError("Failed to write to %s\n%s" % (filename, output))

    def _remoteFileAppendContents(self, filename, data):
        data = Util.escapeDoubleQuotes(data, times=4)

        rc, output = self._nodeShell('"echo \\"%s\\" >> %s"' % (data, filename),
                                     withOutput=True, shell=True)
        if rc != 0:
            Util.printError("Failed to append to %s\n%s" % (filename, output))

    def _filePutContentAsOneAdmin(self, filename, content):
        self.filePutContentsCmd(filename, content)
        self.setOwnerCmd(filename)

    def _remoteChmod(self, path, mode):
        return self._nodeShell('chmod %o %s' % (mode, path))

    def _remoteFileExists(self, path):
        return self._nodeShell('ls %s' % path, sshQuiet=True) == 0

    # -------------------------------------------
    #     General
    # -------------------------------------------

    def setNodeAddr(self, nodeAddr):
        self.nodeAddr = nodeAddr

    def setNodePrivateKey(self, privateKey):
        self.nodePrivateKey = privateKey

    def workOnFrontend(self):
        self.appendOrReplaceInFileCmd = appendOrReplaceInFile
        self.setOwnerCmd = self._setCloudAdminOwner
        self.executeCmd = self._execute
        self.executeCmdWithOutput = self._executeWithOutput
        self.createDirsCmd = self._createDirs
        self.filePutContentsCmd = filePutContent
        self.fileAppendContentsCmd = fileAppendContent
        self.chmodCmd = os.chmod
        self.copyCmd = self._copy
        self.duplicateCmd = self._copy
        self.removeCmd = self._remove

    def workOnNode(self):
        self.appendOrReplaceInFileCmd = self._remoteAppendOrReplaceInFile
        self.setOwnerCmd = self._remoteSetCloudAdminOwner
        self.executeCmd = self._nodeShell
        self.duplicateCmd = self._remoteCopyFile
        self.createDirsCmd = self._remoteCreateDirs
        self.filePutContentsCmd = self._remoteFilePutContents
        self.fileAppendContentsCmd = self._remoteFileAppendContents
        self.chmodCmd = self._remoteChmod
        self.copyCmd = self._nodeCopy
        self.removeCmd = self._remoteRemove

    def configureQuarantine(self):
        filename = os.path.join(Defaults.ETC_DIR, 'quarantine.cfg')
        search = '^PERIOD.*$'
        replace = 'PERIOD=%(quarantinePeriod)s' % self.__dict__
        Util.appendOrReplaceInFile(filename, search, replace)

    def configureCloudProxyService(self):
        self.installPackages(['stratuslab-one-proxy'])
        self._configureProxyDefaultUsers()
        self._restartJetty()

    def _configureProxyDefaultUsers(self):
        self._configureProxyDefaultUsersUsernamePassword()

    def _configureProxyDefaultUsersUsernamePassword(self):
        filename = Defaults.AUTHN_CONFIG_FILE
        search = self.oneUsername
        replace = '%(oneUsername)s=%(proxyOneadminPassword)s,cloud-access' % self.__dict__
        Util.appendOrReplaceInFile(filename, search, replace)

    def _restartJetty(self):
        self.executeCmd('/etc/init.d/one-proxy restart'.split(' '))

    # -------------------------------------------
    # Firewall
    # -------------------------------------------

    # TODO: extract Firewall class from the code below

    DEFAULT_FIREWALL_TABLE = 'filter'

    # redefine in sub-class to point to required file
    FILE_FIREWALL_RULES = '/etc/sysconfig/iptables'

    IP_TABLES_LIST = ['filter','nat','mangle','raw']

    def _configureNetworkInterface(self, device, ip, netmask):
        pass

    def configureFirewall(self):
        self._loadNetfilterModules()

        self._configureFirewallForProxy()
        self._configureFirewallNat()
        self._persistFirewallRules()

    def _configureFirewallForProxy(self):
        port = str(self.onePort)
        rules = ({'table':'filter',
                  'rule' :'-A INPUT -s 127.0.0.1 -p tcp -m tcp --dport %s -j ACCEPT' % port},
                 {'table':'filter',
                  'rule' :'-A INPUT -p tcp -m tcp --dport %s -j REJECT --reject-with icmp-port-unreachable' % port})

        if not self._isSetFirewallRulesAll(rules):
            self._setFirewallRulesAll(rules)

    def _configureFirewallNat(self):
        if self.nat.lower() in ['false', 'no', 'off', '0', '']:
            return None

        self._configureFirewallNatNetworking()

        networkWithMask = '%s/%s' % (self.natNetwork, self.natNetmask)
        rules = ({'table':'nat',
                  'rule':'-A POSTROUTING -s %s -d ! %s -j MASQUERADE' % ((networkWithMask,)*2)},
                  {'table':'filter',
                   'rule':'-A FORWARD -d %s -m state --state RELATED,ESTABLISHED -j ACCEPT' % networkWithMask},
                  {'table':'filter',
                   'rule':'-A FORWARD -d %s -j ACCEPT' % networkWithMask})

        if not self._isSetFirewallRulesAll(rules):
            self._setFirewallRulesAll(rules)

    def _configureFirewallNatNetworking(self):
        self._enableIpForwarding()

        device = self.natNetworkInterface
        ip = getattr(self, 'natGateway', '')
        if not ip:
            ip = Util.gatewayIpFromNetAddress(self.natNetwork)

        self._configureVirtualNetInterface(device, ip,
                                           self.natNetmask)

    @staticmethod
    def enableIpForwarding():
        Util.printDetail('Enabling packets forwarding.')
        file(FILE_IPFORWARD_HOT_ENABLE, 'w').write('1')
        appendOrReplaceInFile(FILE_IPFORWARD_PERSIST,
                              'net.ipv4.ip_forward',
                              'net.ipv4.ip_forward = 1')

    def _enableIpForwarding(self):
        return BaseSystem.enableIpForwarding()

    def _configureVirtualNetInterface(self, device, ip, netmask):
        device = device + ':privlan'

        Util.printDetail('Configuring network interface %s.' % device)
        self._configureNetworkInterface(device, ip, netmask)

        Util.printDetail('Starting network interface %s.' % device)
        self.executeCmd(['ifup', device])

    def _persistFirewallRules(self):
        self._saveFirewallRules(self.FILE_FIREWALL_RULES)


    def _loadNetfilterModules(self):
        # just in case if kernel modules were not yet loaded
        devNull = open(os.path.devnull, 'w')
        for table in self.IP_TABLES_LIST:
            cmd = 'iptables -nL -t %s' % table
            self.executeCmd(cmd.split(), stdout=devNull)
        devNull.close()

    def _saveFirewallRules(self, filename):
        # back-up
        self.executeCmd(('cp -fp %s %s.LAST'%((filename,)*2)).split(' '))

        _,output = self.executeCmdWithOutput(['iptables-save'])
        Util.printDetail('Saving firewall rules to %s.' % filename)
        filePutContent(filename, output)
        os.chmod(filename, 0600)

    def _isSetFirewallRulesAll(self, rules):
        tables = dict.fromkeys([r.get('table', self.DEFAULT_FIREWALL_TABLE)
                                                        for r in rules]).keys()
        currentRules = self._getFirewallRulesPerTable(tables)
        for ruleSpec in rules:
            if not self._isSetFirewallRule(currentRules, ruleSpec):
                return False
        return True

    def _getFirewallRulesPerTable(self, tables=IP_TABLES_LIST):
        rules = {}
        for table in tables:
            rc, output = self.executeCmdWithOutput(('iptables-save -t %s' %
                                                   table).split(' '))
            if rc != 0:
                raise Exceptions.ExecutionException('iptables-save reported an error:\n%s'%
                                         output)
            rules.update({table:output})
        return rules

    def _isSetFirewallRule(self, currentRules, ruleSpec):
        rule, table = self._getRuleAndTableFromRuleSpec(ruleSpec)
        rulesInTable = currentRules[table]

        if re.search(rule, rulesInTable, re.M):
            return True
        return False

    def _setFirewallRulesAll(self, rules):
        self._deleteFirewallRulesAllGiven(rules)

        for ruleSpec in rules:
            self._setFirewallRule(ruleSpec)

    def _deleteFirewallRulesAllGiven(self, rules):
        for ruleSpec in rules:
            self._deleteFirewallRule(ruleSpec)

    def _deleteFirewallRule(self, ruleSpec):
        rule, table = self._getRuleAndTableFromRuleSpec(ruleSpec)
        rule = '-D %s' % rule[3:] # remove action; leave chain and rule

        self.executeCmd(('iptables -t %s %s' % (table,rule)).split(' '))

    def _setFirewallRule(self, ruleSpec):
        rule, table = self._getRuleAndTableFromRuleSpec(ruleSpec)

        self.executeCmd(('iptables -t %s %s' % (table,rule)).split(' '))

    def _getRuleAndTableFromRuleSpec(self, ruleSpec):
        return ruleSpec['rule'], \
               ruleSpec.get('table', self.DEFAULT_FIREWALL_TABLE)

    # -------------------------------------------
    # sendmail
    # -------------------------------------------

    def installSendmail(self):
        package = 'sendmail'
        if getattr(self, 'smtpHost', 'localhost') == 'localhost':
            self.installPackages([self.getPackageName(package)])
        else:
            Util.printDetail('Skipping installation of %s' % package)

    # -------------------------------------------
    # CA
    # -------------------------------------------

    def installCAs(self):
        def _isCertificateAuthority():
            return Util.isTrueConfVal(getattr(self, 'certificateAuthority', False))

        if not _isCertificateAuthority():
            Util.printDetail('Requested not to install CAs.')
        else:
            self._installCAs()
            self._installFetchCrl()
            self._enableFetchCrl()
            self._installVomsFiles()

    def _enableFetchCrl(self):
        pass

    def _installCAs(self):
        packages = []

        if self.certificateAuthorityPackages and self.certificateAuthorityRepo:
            caPackages = map(lambda x: x.strip(),
                             self.certificateAuthorityPackages.split(','))
            packages.extend(caPackages)
            repoConf = '\n'.join([line.strip() for line in self.certificateAuthorityRepo.strip().split('\n')])
            repoName = self.caRepoName
            for package in packages:
                self._updatePackageAndRepoInfo(package, repoName, repoConf)
        else:
            packages.append(self.getPackageName('CA'))

        self.installPackages(packages)

        for package in packages:
            if not self.isPackageInstalled(package):
                Util.printError('Failed to install %s.' % package)

    def installOpenNebula(self):
        Util.printDetail('Installing OpenNebula')
        self.installPackages([self.getPackageName('opennebula')])

    def _installFetchCrl(self):
        package = self.getPackageName('fetch-crl')
        self.installPackages([package])
        if not self.isPackageInstalled(package):
            Util.printError('Failed to install %s.' % package)

    def _installVomsFiles(self):

        r = requests.get(self.voIdCardUrl)
        if r.status_code == requests.codes.ok:
            if not os.path.exists(self.vomsesDir):
                try:
                    os.mkdir(self.vomsesDir)
                except Exception as e:
                    Util.printError('could not create ' + vomsesDir)

            vo_data = ET.fromstring(r.text)

            for idcard in vo_data:
                voname = idcard.attrib['Name']
                vopath = os.path.join(self.vomsesDir, voname)

                if not os.path.exists(vopath):
                    try:
                        os.mkdir(vopath)
                    except Exception as e:
                        Util.printError('could not create ' + vopath)

                for server in idcard.findall('./gLiteConf/VOMSServers/VOMS_Server'):
                    hostname = server.find('hostname')
                    dn = server.find('X509Cert/DN')
                    ca_dn = server.find('X509Cert/CA_DN')
                    if hostname is not None and dn is not None and ca_dn is not None:
                        contents = '%s\n%s\n' % (dn.text, ca_dn.text)
                        path = os.path.join(vopath, hostname.text + '.lsc')
                        try:
                            with open(path, 'w') as f:
                                f.write(contents)
                        except Exception as e:
                            Util.printError('could not create file ' + path)
        else:
            Util.printError('error retrieving VO ID card data from ' + self.voIdCardUrl)

    # -------------------------------------------
    # DHCP server
    # -------------------------------------------

    NET_TYPES_DHCP = ['OnePublicNetwork', 'OneLocalNetwork']

    def configureDhcpServer(self):

        def _dhcpDefined():
            return Util.isTrueConfVal(getattr(self, 'dhcp', 'False'))
        def _dhcpNetTypesDefined():
            return any([Util.isTrueConfVal(getattr(self, self._assembleDhcpAttributeName(v), 'False'))
                                                for v in self.NET_TYPES_DHCP])

        if not _dhcpDefined():
            return
        elif not _dhcpNetTypesDefined():
            return

        Util.printStep('Configuring DHCP service')
        self._installDhcp()
        self._confgureDhcp()
        self._startDhcp()

    def _assembleDhcpAttributeName(self, postfix):
        DHCP_PARAMETER_PREFIX = 'dhcp'
        return '%s%s' % (DHCP_PARAMETER_PREFIX, postfix)

    def _installDhcp(self):
        Util.printDetail('Installing DHCP server.')

        dhcpPackage = self.getPackageName('dhcp')
        self.installPackages([dhcpPackage])

        if not self.isPackageInstalled(dhcpPackage):
            Util.printError('Failed to install %s.' % dhcpPackage)

    def _confgureDhcp(self):

        def _isAllDhcpGroupsDefined(_groups):
            return all(_groups.values())

        def _getConfGlobals():
            _globals = """
ddns-update-style none;
ignore unknown-clients;
ignore bootp;
"""
            if hasattr(self, 'dhcpNtpServers') and self.dhcpNtpServers:
                _globals += 'option ntp-servers %s;\n' % self.dhcpNtpServers
            return _globals

        def _getConfSubnets():
            subnetTemplate = """
subnet %(subnet)s netmask %(netmask)s {
  option routers %(routers)s;
}
"""
            subnet = ''
            # All net types are defined together with NATing. Assuming NATing for
            # Local net type. Need to create a shared network.
            if Util.isTrueConfVal(self.nat) and _isAllDhcpGroupsDefined(dhcpGroups):
                subnet = """
shared-network StratusLab-LAN {
"""
                for _type in self.NET_TYPES_DHCP:
                    subnet += subnetTemplate % {
                               'subnet'  : getattr(self, self._assembleDhcpAttributeName('%sSubnet' % _type)),
                               'netmask' : getattr(self, self._assembleDhcpAttributeName('%sNetmask' % _type)),
                               'routers' : getattr(self, self._assembleDhcpAttributeName('%sRouters' % _type))}
                subnet += "}\n"

            elif Util.isTrueConfVal(self.nat) and dhcpGroups['OneLocalNetwork']:
                subnet = """
shared-network StratusLab-LAN {
"""
                # main interface
                subnet += """
subnet %(subnet)s netmask %(netmask)s {
}
""" % {'subnet'  : self.dhcpSubnet,
       'netmask' : self.dhcpNetmask}
                # virtual interface
                natGateway = getattr(self, 'natGateway', '')
                if not natGateway:
                    natGateway = Util.gatewayIpFromNetAddress(self.natNetwork)
                subnet += subnetTemplate % {'subnet'  : self.natNetwork,
                                            'netmask' : self.natNetmask,
                                            'routers' : natGateway}
                subnet += "}\n"

            elif dhcpGroups['OnePublicNetwork']:
                # main interface
                subnet += """
subnet %(subnet)s netmask %(netmask)s {
}
""" % {'subnet'  : self.dhcpSubnet,
       'netmask' : self.dhcpNetmask}

            elif dhcpGroups['OneLocalNetwork']:
                # virtual interface
                subnet = subnetTemplate % {
                                'subnet'  : self.dhcpOneLocalNetworkSubnet,
                                'netmask' : self.dhcpOneLocalNetworkNetmask,
                                'routers' : self.dhcpOneLocalNetworkRouters}
            else:
                Util.printWarning('Invalid parameters combination to configure DHCP.')

            return subnet

        def _getConfGroups():
            groupHeadTemplate = """
group {
  option broadcast-address %(broadcast)s;
  option subnet-mask %(netmask)s;
  option routers %(routers)s;
  option domain-name "%(domainName)s";
  option domain-name-servers %(nameservers)s;
"""
            hostTemplate = """
  host %(type)s-vm%(id)s {
    hardware ethernet %(mac)s;
    fixed-address %(ip)s;
    max-lease-time %(leaseTime)s;
  }
"""
            groups = ''
            for _type,ipsMacs in dhcpGroups.items():
                if not ipsMacs:
                    continue
                groups += groupHeadTemplate % \
                    {'broadcast'   : getattr(self, self._assembleDhcpAttributeName('%sBroadcast' % _type)),
                     'netmask'     : getattr(self, self._assembleDhcpAttributeName('%sNetmask' % _type)),
                     'routers'     : getattr(self, self._assembleDhcpAttributeName('%sRouters' % _type)),
                     'domainName'  : getattr(self, self._assembleDhcpAttributeName('%sDomainName' % _type)),
                     'nameservers' : getattr(self, self._assembleDhcpAttributeName('%sDomainNameServers' % _type))}

                hosts = ''
                for i,ipMac in enumerate(ipsMacs):
                    hosts += hostTemplate % {'type' : _type.lower(),
                                             'id'  : str(i),
                                             'mac' : ipMac[1],
                                             'ip' : ipMac[0],
                                             'leaseTime' : self.dhcpLeaseTime}
                groups += hosts
                groups += '}\n'

            return groups

        Util.printDetail('Configuring DHCP server.')

        _NOTHING = []
        dhcpGroups = dict.fromkeys(self.NET_TYPES_DHCP, _NOTHING)

        for netType in self.NET_TYPES_DHCP:
            if Util.isTrueConfVal(getattr(self, self._assembleDhcpAttributeName(netType), False)):
                dhcpGroups[netType] = self.__getIpMacTuplesForNetworkType(netType)

        if not any(dhcpGroups.values()):
            Util.printError('When configuring DHCP %s networks IP/MAC pairs should be given.' %
                                ','.join(self.NET_TYPES_DHCP))

        content = _getConfGlobals() + \
                    _getConfSubnets() + \
                    _getConfGroups()

        confFile = self.getPackageConfigFileName('dhcp')

        Util.filePutContent(confFile, content)

    def __getIpMacTuplesForNetworkType(self, _type):
        if _type not in self.NET_TYPES_DHCP:
            Util.printError('Expected one of: %s. Got %s'%(','.join(self.NET_TYPES_DHCP),_type))

        _type = _type.replace(_type[0], _type[0].lower(), 1)

        ips = [x for x in getattr(self, '%sAddr'%_type).split()]
        macs = [x for x in getattr(self, '%sMac'%_type).split()]
        if len(ips) != len(macs):
            Util.printError('%s network: number of IPs should match number of MACs.'%_type)
        return zip(ips, macs)

    def _startDhcp(self):
        Util.printDetail('(Re)Starting DHCP server.')

        serviceName = self.packages['dhcp'].initdScriptName
        rc = self.restartService(serviceName)

        if rc != 0:
            Util.printError('Failed to (re)start DHCP service.')

    # -------------------------------------------
    # DB
    # -------------------------------------------

    def configureDatabase(self):

        if self.oneDbHost in ['localhost', '127.0.0.1']:
            Util.printDetail('Installing MySQL server.')
            mysqlPackage = self.getPackageName('MySQLServer')
            self.installPackages([mysqlPackage])

            Util.printDetail('Starting MySQL server.')
            mysqlService = self.getPackageInitdScriptName('MySQLServer')
            self.startService(mysqlService)

            Util.printDetail('Changing db root password')
            self._configureRootDbUser(self.oneDbRootPassword)

            Util.printDetail('Creating oneadmin db account')
            self._configureDbUser(self.oneDbUsername, self.oneDbPassword)
        else:
            Util.printDetail('Skipping MySQL installation/configuration. It is assumed to be configured on %s' % self.oneDbHost)

    def _configureRootDbUser(self, password):
        rc, output = self._execute(["/usr/bin/mysqladmin", "-uroot", "password", "%s" % password], withOutput=True)
        if rc != 0:
            Util.printWarning("Couldn't set root password. Already set?\n%s" % output)

    def _configureDbUser(self, username, password):
        mysqlCommand = "/usr/bin/mysql -uroot -p%s" % self.oneDbRootPassword
        userCreate = "CREATE USER '%s'@'localhost' IDENTIFIED BY '%s'" % (username, password)
        userGrant =  "GRANT CREATE, DROP, SELECT, INSERT, DELETE, UPDATE, INDEX ON opennebula.* TO '%s'@'localhost'" % username

        rc, output = self._execute("%s -e \"%s\"" % (mysqlCommand, userCreate),
                                   withOutput=True, shell=True)
        if rc != 0:
            Util.printWarning("Couldn't create user '%s'. Already exists?\n%s" % (username, output))

        rc, output = self._execute("%s -e \"%s\"" % (mysqlCommand, userGrant),
                                   withOutput=True, shell=True)
        if rc != 0:
            Util.printError("Error granting permission for user '%s'.\n%s" % (username, output))

    # -------------------------------------------
    # Bridge
    # -------------------------------------------

    def configureBridgeRemotely(self):
        def doNotConfigureBridge():
            return Util.isFalseConfVal(getattr(self, 'nodeBridgeConfigure', True))

        if doNotConfigureBridge():
            Util.printDetail('Asked not to configure bridge')
            return

        checkBridgeCmd = '"brctl show | grep ^%s.*%s$"' % \
                            (self.nodeBridgeName, self.nodeNetworkInterface)
        rc, output = self._nodeShell(checkBridgeCmd, withOutput=True, shell=True)
        if rc == 0:
            Util.printDetail('Bridge already configured')
            return
        else:
            Util.printDetail('Bridge is NOT configured. %s' % output)

        configureBridgeCmd = 'nohup "brctl addbr %(bridge)s; sleep 10; ifconfig %(interf)s 0.0.0.0; sleep 10; brctl addif %(bridge)s %(interf)s; sleep 10; dhclient %(bridge)s"' % \
                            {'bridge' : self.nodeBridgeName,
                             'interf' : self.nodeNetworkInterface}

        rc, output = self._nodeShell(configureBridgeCmd, withOutput=True, shell=True)
        if rc != 0:
            Util.printDetail('Failed to configure bridge.\n%s' % output)
        else:
            sleepTime = 5
            Util.printDetail('Sleeping %i sec for the bridge one the node to come up.' % sleepTime)
            time.sleep(sleepTime)

            Util.printDetail('Testing connection to the node.')
            rc, output = self._nodeShell('true', withOutput=True)
            if rc == 0:
                Util.printDetail('OK.')
            else:
                Util.printError('Could not connect to the node after attempt to configre bridge.\n%s' % output)

            Util.printDetail('Testing if bridge was configured.')
            rc, output = self._nodeShell(checkBridgeCmd, withOutput=True, shell=True)
            if rc == 0:
                Util.printDetail('OK.')
                self._persistRemoteBridgeConfig(self.nodeNetworkInterface, self.nodeBridgeName)
                return
            else:
                Util.printError('Bridge was not configured.\n%s' % output)

    def _persistRemoteBridgeConfig(self):
        pass

    def _writeToFilesRemote(self, listOfFileNameContentTuples):
        tmpFilename = tempfile.mktemp()
        for remoteFilename, content in listOfFileNameContentTuples:
            Util.filePutContent(tmpFilename, content)
            self._nodeCopy(tmpFilename, remoteFilename)
        try:
            os.unlink(tmpFilename)
        except: pass

FILE_IPFORWARD_HOT_ENABLE = '/proc/sys/net/ipv4/ip_forward'
FILE_IPFORWARD_PERSIST = '/etc/sysctl.conf'

def enableIpForwarding():
    return BaseSystem.enableIpForwarding()
