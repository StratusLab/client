import os
import shutil
import subprocess

from Util import appendOrReplaceInFile
from stratuslab.Util import filePutContents, fileGetContents

class BaseSystem(object):
    
    def __init__(self):
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
        self.execute(['scons', '-j2'])

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
        oneKey = fileGetContents('%s/.ssh/id_rsa.pub' % self.ONeHome)
        self.createDirsCmd('%s/.ssh/' % self.ONeHome)
        self.filePutContentsCmd('%s/.ssh/authorized_keys' % self.ONeHome,
              oneKey)
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

    def configureNFSServer(self, networkAddr, networkMask):
        self.appendOrReplaceInFileCmd('/etc/exports', 
            self.ONeHome, '%s %s/%s(rw,async,no_subtree_check)\n' % 
            (self.ONeHome, networkAddr, networkMask))
        self.executeCmd(['exportfs', '-a'])

    def configureNFSClient(self, frontendIP):
        self.createDirsCmd(self.ONeHome)
        self.appendOrReplaceInFileCmd('/etc/fstab', frontendIP,
            '%s:%s %s nfs soft,intr,rsize=32768,wsize=32768,rw 0 0' % (
             frontendIP, self.ONeHome, self.ONeHome))
        self.executeCmd('mount -a')
        
    def configureSSHServer(self):
        pass

    def configureSSHClient(self):
        # TODO: setup ssh authorized keys
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

    def execute(self, command, shell=False):
        self.displayMessage(' '.join(command))
        process = subprocess.Popen(command, shell=shell)
        process.wait()
        return process.returncode

    def ONeAdminExecute(self, command, shell=False):
        su = ['su', '-l', self.ONeAdmin, '-c']
        su.extend(command)
        return self.execute(su, shell)
    
    def setONeAdminOwner(self, path):
        os.chown(path, int(self.ONeAdminUID), int(self.ONeAdminGID)) 
        
    def createDirs(self, path):
        if not os.path.isdir(path) and not os.path.isfile(path):
            os.makedirs(path)
    
    # -------------------------------------------
    #     Node related methods
    # -------------------------------------------
    
    def nodeShell(self, command, **kwargs):
        # kwargs for compatibility with execute command
        if type(command) == type(list()):
            command = ' '.join(command)
            
        return self.remoteCmd(self.nodeAddr, command,
            port=self.nodePort,
            privateKey=self.nodePrivateKey)

    def remoteCmd(self, hostAddr, command, user='root', port=22,
            privateKey=None):
        sshCmd = ['ssh', '-p', str(port), '-l', user, '-F', self.tempSshConf]
        if privateKey is not None and os.path.isfile(privateKey):
            # TODO: with verbose display a message if key not exists
            sshCmd.extend(['-i', privateKey])
        sshCmd.append(hostAddr)
        sshCmd.append(command)
        return self.execute(sshCmd)

    def remoteSetONeAdminOwner(self, path):
        self.nodeShell(['chown %s:%s %s' % (self.ONeAdminUID, 
                                            self.ONeAdminGID, path)])
            
    def remoteCreateDirs(self, path):
        self.nodeShell('mkdir -p %s' % path)
        
    def remoteAppendOrReplaceInFile(self, filename, search, replace):
        res = self.nodeShell(['sed -i \'s#%s.*#%s#\' %s' % (
            search, replace, filename)], shell=True)
        
        # We suppose the file does not exists
        if res != 0:
            self.remoteFilePutContents(filename, replace)
    
    def remoteCopyFile(self, src, dest):
        self.nodeShell(['cp -rf %s %s' % (src, dest)])
        
    def remoteFilePutContents(self, filename, data):
        self.nodeShell('echo "%s" > %s' % (data, filename))
        
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
        