import os
import shutil
from datetime import datetime

from stratuslab.Util import appendOrReplaceInFile
from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import execute
from stratuslab.Util import fileAppendContent
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
import stratuslab.Util as Util
from stratuslab.Util import printDetail

class BaseSystem(object):
    
    def __init__(self):
        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')
        self.workOnFrontend()

    def init(self):
        self._setOneHome()

    # -------------------------------------------
    #     Packages manager and related
    # -------------------------------------------
    
    def updatePackageManager(self):
        pass

    def installWebServer(self):
        pass

    def installPackages(self, packages):
        pass

    def installNodePackages(self, packages):
        pass

    def installFrontendDependencies(self):
        self.updatePackageManager()
        self.installPackages(self.frontendDeps)

    def installNodeDependencies(self):
        self.installNodePackages(self.nodeDeps)

    def installHypervisor(self):
        self.installNodePackages(self.hypervisorDeps.get(self.hypervisor))

    # -------------------------------------------
    #     ONE build and related
    # -------------------------------------------

    def cloneGitRepository(self, buildDir, repoUrl, cloneName, branch):
        self.ONeRepo = repoUrl
        self.ONeSrcDir = buildDir

        self._createDirs(self.ONeSrcDir)
        os.chdir(self.ONeSrcDir)
        self._execute(['git', 'clone', repoUrl, cloneName, '-b', branch])
        os.chdir(cloneName)

#    def buildCloudSystem(self):
#        self._applyPatchs()
#        self.executeCmd(['scons', '-j2'])
        
    def _applyPatchs(self):
        patchDir = os.path.abspath(Util.shareDir + 'patch')
        
        for patch in \
            [os.path.abspath('%s/%s' % (patchDir, f)) for f in os.listdir(patchDir)]:
            patchFile = open(patch, 'rb')
            printDetail('Applying patch %s' % patch, self.verboseLevel)
            self.executeCmd(['patch', '-p1'], stdin=patchFile)
            patchFile.close()

#    def installCloudSystem(self):
#        self._execute(['bash', 'install.sh', '-d', self.oneHome, '-u',
#                      self.oneUsername, '-g', self.oneGroup])

    def startCloudSystem(self):
        self._cloudAdminExecute(['one start'])

    # -------------------------------------------
    #     ONE admin creation
    # -------------------------------------------

    def createCloudGroup(self, groupname, gid):
        self.oneGroup = groupname
        self.oneGid = gid

        self.executeCmd(['groupadd', '-g', self.oneGid, 
                        self.oneGroup])

    def createCloudAdmin(self):

        self.createDirsCmd(os.path.dirname(self.oneHome))
        self.executeCmd(['useradd', '-d', self.oneHome, '-g', 
                        self.oneGroup, '-u', self.oneUid, self.oneUsername,
                        '-s', '/bin/bash', '-p', self.onePassword, '--create-home'])

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
            printDetail('Key file %s already exists, skipping this step' % keyFileName)
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
        
        oneKey = fileGetContent('%s/.ssh/id_rsa' % self.oneHome)
        self._filePutContentAsOneAdmin('%s/.ssh/id_rsa' % self.oneHome, oneKey)
        
        oneKeyPub = fileGetContent('%s/.ssh/id_rsa.pub' % self.oneHome)
        self._filePutContentAsOneAdmin('%s/.ssh/authorized_keys' % self.oneHome,
                                       oneKeyPub)
        self.chmodCmd('%s/.ssh/id_rsa' % self.oneHome, 0600)
        self._configureCloudAdminSsh()

    def _configureCloudAdminSsh(self):
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.oneHome, 
                                      'Host', 'Host *')
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.oneHome, 
                                      '\tStrictHost', '\tStrictHostKeyChecking no')

    def configureCloudAdminAccount(self):
        oneAuthFile = '%s/.one/one_auth' % self.oneHome
        self.appendOrReplaceInFileCmd(oneAuthFile, 
                                      self.oneUsername, '%s:%s' % (self.oneUsername, self.onePassword))

    def _setOneHome(self):
        if not self.oneHome:
            self.oneHome = os.path.expanduser('~' + self.oneUsername)

    # -------------------------------------------
    #     File sharing configuration
    # -------------------------------------------

    def configureNewNfsServer(self, mountPoint, networkAddr, networkMask):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/exports', 
                                      mountPoint, '%s %s/%s(rw,async,no_subtree_check,no_root_squash)' %
                                      (mountPoint, networkAddr, networkMask))
        self.executeCmd(['exportfs', '-a'])

    def configureExistingNfsShare(self, shareLocation, mountPoint):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/fstab', shareLocation,
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

    def _configureXen(self):
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.oneUsername,
                                      '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xm *' % self.oneUsername)
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.oneUsername,
                                      '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xentop *' % self.oneUsername)
        self.executeCmd(['sed -i -E \'s/Defaults[[:space:]]+requiretty/#&/\''
                        ' /etc/sudoers'])

    # -------------------------------------------
    #     Front-end related methods
    # -------------------------------------------

    def _execute(self, command, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)
        
        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']
        
        return execute(command, 
                       stdout=stdout, 
                       stderr=stderr, 
                       verboseLevel=self.verboseLevel, 
                       verboseThreshold=Util.DETAILED_VERBOSE_LEVEL, 
                       **kwargs)

    def _cloudAdminExecute(self, command, **kwargs):
        su = ['su', '-l', self.oneUsername, '-c']
        su.extend(command)
        return self._execute(su, **kwargs)
    
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
    
    def configureNetwork(self, networkInterface, bridge):
        pass
    
    def _nodeShell(self, command, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        if type(command) == type(list()):
            command = ' '.join(command)

        return sshCmd(command, 
                      self.nodeAddr, 
                      self.nodePrivateKey,
                      stdout=stdout, 
                      stderr=stderr,
                      verboseLevel=self.verboseLevel,
                      verboseThreshold=Util.DETAILED_VERBOSE_LEVEL, 
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
                   verboseThreshold=Util.DETAILED_VERBOSE_LEVEL, 
                   **kwargs)

    def _remoteSetCloudAdminOwner(self, path):
        self._nodeShell(['chown %s:%s %s' % (self.oneUid, 
                        self.oneGid, path)])
            
    def _remoteCreateDirs(self, path):
        self._nodeShell('mkdir -p %s' % path)
        
    def _remoteAppendOrReplaceInFile(self, filename, search, replace):
        res = self._nodeShell(['grep', search, filename])

        if self._patternExists(res):
            self._nodeShell(['sed -i \'s#%s.*#%s#\' %s' % (
                            search, replace, filename)], shell=True)
        else:
            self._remoteFileAppendContents(filename, replace)

    def _patternExists(self, returnCode):
        return returnCode == 0
    
    def _remoteCopyFile(self, src, dest):
        self._nodeShell(['cp -rf %s %s' % (src, dest)])

    def _remoteRemove(self, path):
        self._nodeShell(['rm -rf %s' % path])
        
    def _remoteFilePutContents(self, filename, data):
        self._nodeShell('echo \'%s\' > %s' % (data, filename))

    def _remoteFileAppendContents(self, filename, data):
        self._nodeShell('echo \'%s\' >> %s' % (data, filename))
        
    def _filePutContentAsOneAdmin(self, filename, content):
        self.filePutContentsCmd(filename, content)
        self.setOwnerCmd(filename)

    def _remoteChmod(self, path, mode):
        return self._nodeShell('chmod %o %s' % (mode, path))
        
    # -------------------------------------------
    #     General
    # -------------------------------------------
    
    def setNodeAddr(self, nodeAddr):
        self.nodeAddr = nodeAddr

    def setNodePort(self, nodePort):
        self.nodePort = nodePort

    def setNodePrivateKey(self, privateKey):
        self.nodePrivateKey = privateKey

    def setNodeHypervisor(self, hypervisor):
        self.hypervisor = hypervisor

    def setCloudAdminName(self, username):
        self.oneUsername = username

    def workOnFrontend(self):
        self.appendOrReplaceInFileCmd = appendOrReplaceInFile
        self.setOwnerCmd = self._setCloudAdminOwner
        self.executeCmd = self._execute
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
