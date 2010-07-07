# -*- coding: utf-8 -*-
import os
import shutil
import subprocess

class Base(object):

    def installDependencies(self):
        self.updatePackageManager()
        self.installPackages(self.frontendDeps)

    def updatePackageManager(self):
        pass

    def installPackages(self, packages):
        pass

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
        self.setONeAdminOwner(os.getcwd())
        self.execute(['bash', 'install.sh', '-d', self.ONeHome, '-u',
            self.ONeAdmin, '-g', self.ONeAdminGroup])

    def startONeDaemon(self):
        self.ONeAdminExecute(['one start'])

    def createONeGroup(self, groupname, gid):
        self.ONeAdminGroup =  groupname
        self.ONeAdminGID = gid

        self.execute(['groupadd', '-g', gid,  groupname])

    def createONeAdmin(self, username, uid, homeDir, password):
        self.ONeAdmin = username
        self.ONeHome = homeDir
        self.ONeAdminUID = uid
        self.ONeAdminPassword = password

        self.createDirs(self.ONeHome)
        self.setONeAdminOwner(self.ONeHome)
        self.execute(['useradd', '-d', self.ONeHome, '-g', self.ONeAdminGroup, '-u', uid,
            username, '-s', '/bin/bash', '-p', password, '--create-home'])

    def configureONeAdminEnv(self):  
        self.append2file('%s/.bashrc' % self.ONeHome, 
            'export ONE_LOCATION=%s\n' % self.ONeHome)
        self.append2file('%s/.bashrc' % self.ONeHome, 
            'export ONE_XMLRPC=http://localhost:2633/RPC2\n')
        self.append2file('%s/.bashrc' % self.ONeHome, 
            'export PATH=%s/bin:%s\n' % (self.ONeHome, os.getenv('PATH')))

        self.append2file('%s/.bash_login' % self.ONeHome, 
            '[ -f ~/.bashrc ] && source ~/.bashrc\n')
        self.setONeAdminOwner('%s/.bash_login' % self.ONeHome)

        # Hack to always load .bashrc
        self.execute(['sed -i \'s/\[ -z \\\"\$PS1\\\" \\] \\&\\& ' 
            'return/#&/\' %s/.bashrc' % self.ONeHome], shell=True)

    def configureONeAdminAuth(self):
        self.createDirs('%s/.one' % self.ONeHome)
        self.setONeAdminOwner('%s/.one' % self.ONeHome)

        self.append2file('%s/.one/one_auth' % self.ONeHome, '%s:%s' 
            % (self.ONeAdmin, self.ONeAdminPassword))
        self.setONeAdminOwner('%s/.one/one_auth' % self.ONeHome)

    def setupONeAdminSSHCred(self, keysPath):
        self.createDirs('%s/.ssh/' % self.ONeHome)
        self.setONeAdminOwner('%s/.ssh/' % self.ONeHome)
        self.execute(['ssh-keygen -f %s -N "" -q' % keysPath],
            shell=True) 
        self.setONeAdminOwner(keysPath)
        self.setONeAdminOwner('%s.pub' % keysPath)

        shutil.copy('%s.pub' % keysPath, 
            '%s/.ssh/authorized_keys' % self.ONeHome)
        self.setONeAdminOwner('%s/.ssh/authorized_keys' % self.ONeHome)
        self.append2file('%s/.ssh/config' % self.ONeHome, 
            'Host *\n\tStrictHostKeyChecking no')

    def configureNFS(self, networkAddr, networkMask):
        self.append2file('/etc/exportfs', 
            '%s %s/%s(rw,async,no_subtree_check)' % 
            (self.ONeHome, networkAddr, networkMask))
        self.execute(['exportfs', '-a'])

    def configureSSH(self):
        pass

    def append2file(self, filename, content):
        fd = open(filename, 'a+')
        fd.write(content)
        fd.close()

    def execute(self, command, shell=False):
        print '%s\nCOMMAND: %s\n%s' % ('*' * 60, ' '.join(command), '*' * 60) 
    	process = subprocess.Popen(command, shell=shell)
        process.wait()

    def ONeAdminExecute(self, command, shell=False):
        su = ['su', '-l', self.ONeAdmin, '-c']
        su.extend(command)
        self.execute(su, shell)

    def setONeAdminOwner(self, path):
        os.chown(path, int(self.ONeAdminUID), int(self.ONeAdminGID)) 
    
    def createDirs(self, path):
        if not os.path.isdir(path) and not os.path.isfile(path):
            os.makedirs(path)

