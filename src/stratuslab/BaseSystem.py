import os
import shutil
import subprocess
from datetime import datetime

from Util import appendOrReplaceInFile
from Util import filePutContent, fileGetContent

class BaseSystem(object):
    
    def __init__(self):
        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')
        self.workOnFrontend()
    
    # -------------------------------------------
    #     Packages manager and related
    # -------------------------------------------
    
    def updatePackageManager(self):
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

    def buildCloudSystem(self):
        self._applyPatchs()
        self.executeCmd(['scons', '-j2'])
        
    def _applyPatchs(self):
        patchDir = os.path.abspath('%s/../../share/patch' % os.path.abspath(__file__))
        
        for patch in [os.path.abspath('%s/%s' % (patchDir, f)) 
                      for f in os.listdir(patchDir)]:
            patchFile = open(patch, 'rb')
            self.executeCmd(['patch', '-p1'], stdin=patchFile)
            patchFile.close()

    def installCloudSystem(self):
        self._execute(['bash', 'install.sh', '-d', self.ONeHome, '-u',
            self.ONeAdmin, '-g', self.ONeAdminGroup])

    def startCloudSystem(self):
        self._cloudAdminExecute(['one start'])

    # -------------------------------------------
    #     ONE admin creation
    # -------------------------------------------

    def createCloudGroup(self, groupname, gid):
        self.ONeAdminGroup =  groupname
        self.ONeAdminGID = gid

        self.executeCmd(['groupadd', '-g', self.ONeAdminGID, 
              self.ONeAdminGroup])

    def createCloudAdmin(self, username, uid, homeDir, password):
        self.ONeAdmin = username
        self.ONeHome = homeDir
        self.ONeAdminUID = uid
        self.ONeAdminPassword = password

        self.createDirsCmd(os.path.dirname(self.ONeHome))
        self.executeCmd(['useradd', '-d', self.ONeHome, '-g', 
             self.ONeAdminGroup, '-u', self.ONeAdminUID, self.ONeAdmin,
            '-s', '/bin/bash', '-p', self.ONeAdminPassword, '--create-home'])

    # -------------------------------------------
    #     ONE admin env config and related
    # -------------------------------------------

    def configureCloudAdminEnv(self, ONeDPort):
        self.ONeDPort = ONeDPort

        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.ONeHome,
            'export ONE_LOCATION', 
            'export ONE_LOCATION=%s' % self.ONeHome)
        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.ONeHome, 
            'export ONE_XMLRPC', 
            'export ONE_XMLRPC=http://localhost:%s/RPC2' % self.ONeDPort)
        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.ONeHome,
            'export PATH', 
            'export PATH=%s/bin:%s' % (self.ONeHome, os.getenv('PATH')))

        self.filePutContentsCmd('%s/.bash_login' % self.ONeHome,
            '[ -f ~/.bashrc ] && source ~/.bashrc')
        self.setOwnerCmd('%s/.bash_login' % self.ONeHome)

        # Hack to always load .bashrc
        self.executeCmd(['sed -i \'s/\[ -z \\\"\$PS1\\\" \\] \\&\\& ' 
            'return/#&/\' %s/.bashrc' % self.ONeHome], shell=True)


    def _configureCloudAdminSsh(self):
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.ONeHome, 
              'Host', 'Host *')
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.ONeHome, 
              '\tStrictHost', '\tStrictHostKeyChecking no')

    def configureCloudAdminSshKeys(self):
        keyName = '%s/.ssh/id_rsa' % self.ONeHome
        
        self.createDirsCmd(os.path.dirname(keyName))
        self.setOwnerCmd(os.path.dirname(keyName))
        self.executeCmd(['ssh-keygen -f %s -N "" -q' % keyName],
            shell=True) 
        self.setOwnerCmd(keyName)
        self.setOwnerCmd('%s.pub' % keyName)

        self.copyCmd('%s.pub' % keyName, 
            '%s/.ssh/authorized_keys' % self.ONeHome)
        self.setOwnerCmd('%s/.ssh/authorized_keys' % self.ONeHome)
        self._configureCloudAdminSsh()

    def configureCloudAdminSshKeysNode(self):
        self.createDirsCmd('%s/.ssh/' % self.ONeHome)
        self.setOwnerCmd('%s/.ssh/' % self.ONeHome)
        
        oneKey = fileGetContent('%s/.ssh/id_rsa' % self.ONeHome)
        self._filePutContentAsOneAdmin('%s/.ssh/id_rsa' % self.ONeHome, oneKey)
        
        oneKeyPub = fileGetContent('%s/.ssh/id_rsa.pub' % self.ONeHome)
        self._filePutContentAsOneAdmin('%s/.ssh/authorized_keys' % self.ONeHome,
              oneKeyPub)
        
        self._configureCloudAdminSsh()

    def configureCloudAdminAccount(self):
        self.createDirsCmd('%s/.one' % self.ONeHome)
        self.setOwnerCmd('%s/.one' % self.ONeHome)

        self.appendOrReplaceInFileCmd('%s/.one/one_auth' % self.ONeHome, 
            self.ONeAdmin, '%s:%s' % (self.ONeAdmin, self.ONeAdminPassword))
        self.setOwnerCmd('%s/.one/one_auth' % self.ONeHome)

    # -------------------------------------------
    #     File sharing configuration
    # -------------------------------------------

    def configureNewNfsServer(self, mountPoint, networkAddr, networkMask):
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

    def configureSshClient(self):
        pass

    # -------------------------------------------
    #     Hypervisor configuration
    # -------------------------------------------

    def configureHypervisor(self):
        if self.hypervisor == 'xen':
            self._configureXen()
        elif self.hypervisor == 'kvm':
            self._configureKvm()

    def _configureKvm(self):
        pass

    def _configureXen(self):
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.ONeAdmin,
            '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xm *' % self.ONeAdmin)
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.ONeAdmin,
            '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xentop *' % self.ONeAdmin)
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
        
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, **kwargs)
        process.wait()
        return process.returncode

    def _cloudAdminExecute(self, command, **kwargs):
        su = ['su', '-l', self.ONeAdmin, '-c']
        su.extend(command)
        return self._execute(su, **kwargs)
    
    def _setCloudAdminOwner(self, path):
        os.chown(path, int(self.ONeAdminUID), int(self.ONeAdminGID)) 
        
    def _createDirs(self, path):
        if not os.path.isdir(path) and not os.path.isfile(path):
            os.makedirs(path)
    
    # -------------------------------------------
    #     Node related methods
    # -------------------------------------------
    
    def configureNetwork(self, networkInterface, bridge):
        pass
    
    def _nodeShell(self, command, **kwargs):
        if type(command) == type(list()):
            command = ' '.join(command)
            
        return self._remoteCmd(self.nodeAddr, command,
            port=self.nodePort,
            privateKey=self.nodePrivateKey, **kwargs)

    def _remoteCmd(self, hostAddr, command, user='root', port=22,
            privateKey=None, **kwargs):
        sshCmd = ['ssh', '-p', str(port), '-l', user, '-F', self.tempSshConf]
        if privateKey and os.path.isfile(privateKey):
            sshCmd.extend(['-i', privateKey])
        else:
            print 'key %s does not exists, skip it' % privateKey
        sshCmd.append(hostAddr)
        sshCmd.append(command)
        return self._execute(sshCmd, **kwargs)

    def _remoteSetCloudAdminOwner(self, path):
        self._nodeShell(['chown %s:%s %s' % (self.ONeAdminUID, 
                                            self.ONeAdminGID, path)])
            
    def _remoteCreateDirs(self, path):
        self._nodeShell('mkdir -p %s' % path)
        
    def _remoteAppendOrReplaceInFile(self, filename, search, replace):
        res = self._nodeShell(['grep', search, filename])

        if self._patternExists(res):
            self._nodeShell(['sed -i \'s#%s.*#%s#\' %s' % (
                search, replace, filename)], shell=True)
        else:
            self._remoteFilePutContents(filename, replace)

    def _patternExists(self, returnCode):
        return returnCode == 0
    
    def _remoteCopyFile(self, src, dest):
        self._nodeShell(['cp -rf %s %s' % (src, dest)])
        
    def _remoteFilePutContents(self, filename, data):
        self._nodeShell('echo "%s" >> %s' % (data, filename))
        
    def _filePutContentAsOneAdmin(self, filename, content):
        self.filePutContentsCmd(filename, content)
        self.setOwnerCmd(filename)
        
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
        self.ONeAdmin = username

    def workOnFrontend(self):
        self.appendOrReplaceInFileCmd = appendOrReplaceInFile
        self.setOwnerCmd = self._setCloudAdminOwner
        self.executeCmd = self._execute
        self.copyCmd = shutil.copy
        self.createDirsCmd = self._createDirs
        self.filePutContentsCmd = filePutContent
        
    def workOnNode(self):
        self.appendOrReplaceInFileCmd = self._remoteAppendOrReplaceInFile
        self.setOwnerCmd = self._remoteSetCloudAdminOwner
        self.executeCmd = self._nodeShell
        self.copyCmd = self._remoteCopyFile
        self.createDirsCmd = self._remoteCreateDirs
        self.filePutContentsCmd = self._remoteFilePutContents
        self.tempSshConf = '/tmp/stratus-ssh.tmp.cfg'
        self._generateTempSshConfig(self.tempSshConf)
        
    def _generateTempSshConfig(self, path):
        if not os.path.isfile(path):
            filePutContent(path, 'Host *\n\tStrictHostKeyChecking no')
        
