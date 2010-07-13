import os
import tarfile

from stratuslab.BaseSystem import BaseSystem
from stratuslab.Util import wget

class CentOS(BaseSystem):

    def __init__(self):
        self.systemName = 'CentOS 5.5'
        self.arch = self.getSystemArch()
        self.installCmd = 'yum -q -y --nogpgcheck install'
        self.remotePackages = [
            'http://download.fedora.redhat.com/pub/epel/5/i386/'
                'epel-release-5-3.noarch.rpm',
            'http://prdownloads.sourceforge.net/scons/'
                'scons-1.2.0-1.noarch.rpm',
            'http://centos.karan.org/el5/extras/testing/%(arch)s/RPMS/'
                'xmlrpc-c-1.06.18-1.el5.kb.%(arch)s.rpm' % (
                {'arch': self.arch}),
            'http://centos.karan.org/el5/extras/testing/%(arch)s/RPMS/'
                'xmlrpc-c-devel-1.06.18-1.el5.kb.%(arch)s.rpm' % (
                {'arch': self.arch}),
        ]
        self.remoteSources = [
            'http://kernel.org/pub/software/scm/git/git-1.7.1.1.tar.gz',
            'http://www.sqlite.org/sqlite-amalgamation-3.6.17.tar.gz',
        ]
        self.frontendBuildDeps = ['gcc', 'gcc-c++', 'zlib-devel']
        self.frontendDeps = [ 
            'ruby', 'ruby-devel', 'ruby-ri', 'ruby-irb'
        ]
        self.nodeDeps = ['ruby']
        self.hypervisorDeps = {
            'xen': ['xen', 'kernel-xen'],
            'kvm': ['kvm'],
        }
        self.fileSharingFrontendDeps = {
            'nfs': [],
            'ssh': [],
        }
        self.fileSharingNodeDeps = {
            'nfs': [],
            'ssh': [],
        }
        super(BaseSystem,self).__init__()

    def getSystemArch(self):
        _, _, _, _, arch = os.uname()

        if arch == 'x86_64':
            return arch
        else:
            return 'i386' 

    def updatePackageManager(self):
        pass

    def installPackages(self, packages):
        if len(packages) < 1:
            return

        cmd = self.installCmd.split(' ')
        cmd.extend(packages)
        self.execute(cmd)

    def installNodePackages(self, packages):
        if len(packages) > 0:
            self.nodeShell('%s %s' % 
                (self.installCmd, ' '.join(packages)))

    def installFrontendDependencies(self):
        self.installPackages(self.frontendBuildDeps)
        self.installRemotePackages(self.remotePackages)
        super(CentOS, self).installFrontendDependencies()
        self.installSourceDependencies()

    def installSourceDependencies(self):
        for dep in self.remoteSources:
            self.buildAndInstall(dep)

    def buildAndInstall(self, sourceAddr):
        archive = '/tmp/stratus-deps-src.tar.gz'
        wget(sourceAddr, archive)
        tar = tarfile.open(archive)
        srcFile = tar.getmembers()

        for elem in srcFile:
            tar.extract(elem)

        os.chdir(srcFile[0].name)
        self.execute(['./configure'])
        self.execute(['make', '-j2', 'install'])
        os.chdir('../')

   
    def installRemotePackages(self, packages):
        rpmName = '/tmp/stratus-%d.rpm'
        pkgList = []

        for i in range(len(packages)):
            pkg = packages.pop()
            wget(pkg, rpmName % i)
            pkgList.append(rpmName % i)

        self.installPackages(pkgList)
        
    def configureNFSServer(self, networkAddr, networkMask):
        super(CentOS, self).configureNFSServer(networkAddr, networkMask)
        self.execute(['service', 'nfs', 'start'])


system = CentOS()

