import os
import shutil
import subprocess

from Util import appendOrReplaceInFile
from Util import filePutContents, fileGetContents

class BaseSystem(object):
    
    def __init__(self):
        # Patch are in the root directory of the app
        self.openNebulaPatchs = ['centos-001.patch']
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

        self.createDirs(self.ONeSrcDir)
        os.chdir(self.ONeSrcDir)
        self.execute(['git', 'clone', repoUrl, cloneName, '-b', branch])
        os.chdir(cloneName)

    def buildOpenNebula(self):
        self.patchOpenNebula()
        self.execute(['scons', '-j2'])
        
    def patchOpenNebula(self):
        patchDir = os.path.abspath('%s/../../' % os.path.abspath(__file__))
        
        for patch in self.openNebulaPatchs:
            if os.path.isfile('%s/%s' % (patchDir, patch)):
                patchFile = open('%s/%s' % (patchDir, patch), 'rb')
                self.executeCmd(['patch', '-p1'], stdin=patchFile)
                patchFile.close()

    def installOpenNebula(self):
        self.execute(['bash', 'install.sh', '-d', self.ONeHome, '-u',
            self.ONeAdmin, '-g', self.ONeAdminGroup])

    def startONeDaemon(self):
        self.ONeAdminExecute(['one start'])

    # -------------------------------------------
    #     ONE admin creation
    # -------------------------------------------

    def createONeGroup(self, groupname, gid):
        self.ONeAdminGroup =  groupname
        self.ONeAdminGID = gid

        self.executeCmd(['groupadd', '-g', self.ONeAdminGID, 
              self.ONeAdminGroup])

    def createONeAdmin(self, username, uid, homeDir, password):
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

    def configureONeAdminEnv(self, ONeDPort):
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

    def setupONeAdminSSHCred(self):
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
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.ONeHome, 
            'Host', 'Host *')
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.ONeHome,
            '\tStrictHost', '\tStrictHostKeyChecking no')

    def configureNodeSshCred(self):
        self.createDirsCmd('%s/.ssh/' % self.ONeHome)
        oneKey = fileGetContents('%s/.ssh/id_rsa' % self.ONeHome)
        self.filePutContentsCmd('%s/.ssh/id_rsa' % self.ONeHome, oneKey)
        oneKeyPub = fileGetContents('%s/.ssh/id_rsa.pub' % self.ONeHome)
        self.filePutContentsCmd('%s/.ssh/authorized_keys' % self.ONeHome,
              oneKeyPub)
        # FIXME: See to set user rights

    def configureONeAdminAuth(self):
        self.createDirsCmd('%s/.one' % self.ONeHome)
        self.setOwnerCmd('%s/.one' % self.ONeHome)

        self.appendOrReplaceInFileCmd('%s/.one/one_auth' % self.ONeHome, 
            self.ONeAdmin, '%s:%s' % (self.ONeAdmin, self.ONeAdminPassword))
        self.setOwnerCmd('%s/.one/one_auth' % self.ONeHome)

    # -------------------------------------------
    #     File sharing configuration
    # -------------------------------------------

    def configureNFSServer(self, mountPoint, networkAddr, networkMask):
        self.appendOrReplaceInFileCmd('/etc/exports', 
            mountPoint, '%s %s/%s(rw,async,no_subtree_check,no_root_squash)' % 
            (mountPoint, networkAddr, networkMask))
        self.executeCmd(['exportfs', '-a'])

    def configureNfsShare(self, shareLocation, mountPoint):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/fstab', shareLocation,
            '%s %s nfs soft,intr,rsize=32768,wsize=32768,rw 0 0' % (
             shareLocation, mountPoint))
        self.executeCmd(['mount', '-a'])
        
    def configureSSHServer(self):
        pass

    def configureSSHClient(self):
        pass

    # -------------------------------------------
    #     Hypervisor configuration
    # -------------------------------------------

    def configureHypervisor(self):
        if self.hypervisor == 'xen':
            self.configureXEN()
        elif self.hypervisor == 'kvm':
            self.configureKVM()

    def configureKVM(self):
        pass

    def configureXEN(self):
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.ONeAdmin,
            '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xm, /usr/sbin/xentop' % (
            self.ONeAdmin))

    # -------------------------------------------
    #     Front-end related methods
    # -------------------------------------------

    def execute(self, command, **kwargs):
        self.displayMessage(' '.join(command))
        process = subprocess.Popen(command, **kwargs)
        process.wait()
        return process.returncode

    def ONeAdminExecute(self, command, **kwargs):
        su = ['su', '-l', self.ONeAdmin, '-c']
        su.extend(command)
        return self.execute(su, **kwargs)
    
    def setONeAdminOwner(self, path):
        os.chown(path, int(self.ONeAdminUID), int(self.ONeAdminGID)) 
        
    def createDirs(self, path):
        if not os.path.isdir(path) and not os.path.isfile(path):
            os.makedirs(path)
    
    # -------------------------------------------
    #     Node related methods
    # -------------------------------------------
    
    def nodeShell(self, command, **kwargs):
        if type(command) == type(list()):
            command = ' '.join(command)
            
        return self.remoteCmd(self.nodeAddr, command,
            port=self.nodePort,
            privateKey=self.nodePrivateKey, **kwargs)

    def remoteCmd(self, hostAddr, command, user='root', port=22,
            privateKey=None, **kwargs):
        sshCmd = ['ssh', '-p', str(port), '-l', user, '-F', self.tempSshConf]
        if privateKey is not None and os.path.isfile(privateKey):
            print 'key %s does not exists, skip it' % privateKey
            sshCmd.extend(['-i', privateKey])
        sshCmd.append(hostAddr)
        sshCmd.append(command)
        return self.execute(sshCmd, **kwargs)

    def remoteSetONeAdminOwner(self, path):
        self.nodeShell(['chown %s:%s %s' % (self.ONeAdminUID, 
                                            self.ONeAdminGID, path)])
            
    def remoteCreateDirs(self, path):
        self.nodeShell('mkdir -p %s' % path)
        
    def remoteAppendOrReplaceInFile(self, filename, search, replace):
        res = self.nodeShell(['grep', search, filename])

        if self.patternExists(res):
            self.nodeShell(['sed -i \'s#%s.*#%s#\' %s' % (
                search, replace, filename)], shell=True)
        else:
            self.remoteFilePutContents(filename, replace)

    def patternExists(self, returnCode):
        return returnCode == 0
    
    def remoteCopyFile(self, src, dest):
        self.nodeShell(['cp -rf %s %s' % (src, dest)])
        
    def remoteFilePutContents(self, filename, data):
        self.nodeShell('echo "%s" >> %s' % (data, filename))
        
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

    def setONeAdmin(self, username):
        self.ONeAdmin = username

    def displayMessage(self, *msg):
        print '\n\n\n%s\nExecuting: %s\n%s\n' % (
            '-' * 60, ' '.join(msg), '-' * 60) 

    def workOnFrontend(self):
        self.appendOrReplaceInFileCmd = appendOrReplaceInFile
        self.setOwnerCmd = self.setONeAdminOwner
        self.executeCmd = self.execute
        self.copyCmd = shutil.copy
        self.createDirsCmd = self.createDirs
        self.filePutContentsCmd = filePutContents
        
    def workOnNode(self):
        self.appendOrReplaceInFileCmd = self.remoteAppendOrReplaceInFile
        self.setOwnerCmd = self.remoteSetONeAdminOwner
        self.executeCmd = self.nodeShell
        self.copyCmd = self.remoteCopyFile
        self.createDirsCmd = self.remoteCreateDirs
        self.filePutContentsCmd = self.remoteFilePutContents
        self.tempSshConf = '/tmp/stratus-ssh.tmp.cfg'
        self.genTempSshConf(self.tempSshConf)
        
    def genTempSshConf(self, path):
        if not os.path.isfile(path):
            filePutContents(path, 'Host *\n\tStrictHostKeyChecking no')
        
