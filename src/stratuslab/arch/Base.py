# -*- coding: utf-8 -*-
import os
import shutil
import subprocess

class Base(object):

    def __init__(self):
        os.makedirs(self.buildDir)
        os.chdir(self.buildDir)

    def installDependencies(self):
        self.updatePackageManager()
        self.installPackages(self.frontendDeps)

    def cloneGitRepository(self, repoUrl, cloneName, branch):
        self.ONeRepo = repoUrl
        self.ONeSrcDir = os.path.abspath('%s/%s' %
        (os.path.abspath(os.path.dirname(__file__)), cloneName))

        self.execute(['git', 'clone', repoUrl, cloneName, '-b', branch])

    def buildOpenNebula(self):
        os.chdir(self.ONeSrcDir)
        self.execute(['scons', '-j2'])

    def installOpenNebula(self):
        os.chdir(self.ONeHome)
        self.ONeAdminExecute(['/bin/bash', 'install.sh', '-d',
            self.ONeHome])

    def startONeDaemon(self):
        self.ONeAdminExecute(['one', 'start'])

    def createONeGroup(self, groupname, gid):
        self.ONeAdminGroup =  groupname
        self.ONeAdminGID = gid

        self.execute(['groupadd', '-g', gid,  groupname])

    def createONeAdmin(self, username, uid, homeDir, password):
        self.ONeAdmin = username
        self.ONeHome = homeDir
        self.ONeAdminUID = uid
        self.ONeAdminPassword = password

        os.makedirs(ONeHome)
        self.execute(['useradd', '-d', self.ONeHome, '-g', self.ONeAdminGroup, '-u', uid,
            username, '-s', '/bin/bash', '-p', password, '--create-home'])

    def configureONeAdminEnv(self):  
        self.append2File('%s/.bashrc' % self.ONeHome, 
            'export ONE_LOCATION=%s' % self.ONeHome)
        self.append2File('%s/.bashrc' % self.ONeHome, 
            'export ONE_XMLRPC=http://localhost:2633/RPC2')
        self.append2File('%s/.bashrc' % self.ONeHome, 
            'export PATH=%s/bin:%s' % (self.ONeHome, os.getenv('PATH')))

        self.append2File('%s/.bash_login' % self.ONeHome, 
            '[ -f ~/.bashrc ] && source ~/.bashrc')
        self.setONeAdminOwner('%s/.bash_login' % self.ONeHome)

        # Hack to always load .bashrc
        self.append2File('%s/.bashrc' % self.ONeHome, 
            "sed -i 's/\[ -z \"\$PS1\" \] \&\& return/#&/'")

    def configureONeAdminAuth(self):
        os.makedirs('%s/.one' % self.ONeHome)
        self.setONeAdminOwner('%s/.one' % self.ONeHome)

        self.append2File('%s/.one/one_auth' % self.ONeHome, '%s:%s' 
            % (self.ONeAdmin, self.ONeAdminPassword))
        self.setONeAdminOwner('%s/.one/one_auth' % self.ONeHome)

    def setupONeAdminSSHCred(self, keysPath):
        self.ONeAdminExecute(['ssh-keygen', '-f', keysPath, 
            '-N', '""', '-q'])
        shutil.copy('%s.pub' % keysPath, 
            '%s/.ssh/authorized_keys' % self.ONeHome)
        self.setONeAdminOwner('%s/.ssh/authorized_keys' % self.ONeHome)
        self.append2File('%s/.ssh/config' % self.ONeHome, 
            'Host *\n\tStrictHostKeyChecking no')

    def append2file(self, filename, content):
        fd = open(filename, 'a')
        fd.write(content)
        fd.close()

    def execute(self, command):
    	subprocess.Popen(command)

    def ONeAdminExecute(self, command):
        self.execute(['su', '-', self.ONeAdmin, '-c'].extend(command))

    def setONeAdminOwner(self, path):
        os.chown(path, self.ONeAdminUID, self.ONeAdminGID) 

