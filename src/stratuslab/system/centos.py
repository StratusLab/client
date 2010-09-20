import os
import tarfile

from stratuslab.BaseSystem import BaseSystem
from stratuslab.Util import wget
from stratuslab.system.PackageInfo import PackageInfo

class CentOS(BaseSystem):

    def __init__(self):
        self.systemName = 'CentOS 5.5'
        self.arch = self.getSystemArch()
        self.installCmd = 'yum -q -y --nogpgcheck install'
        self.remotePackages = [
            # ('name', 'version', 'arch', 'uri')
            # --> <uri>/<name>-<version>.<arch>.rpm
            ('scons', '1.2.0-1', 'noarch', 'http://prdownloads.sourceforge.net/scons'),
            ('xmlrpc-c', '1.06.18-1.el5.kb', self.arch, 'http://centos.karan.org/el5/extras/testing/%(arch)s/RPMS'),
            ('xmlrpc-c-devel', '1.06.18-1.el5.kb', self.arch, 'http://centos.karan.org/el5/extras/testing/%(arch)s/RPMS'),
        ]
        self.remoteSources = [
            # ('name', 'version', 'uri', 'extension')
            # --> <uri>/<name>-<version>.<extention>
            ('git', '1.7.1.1', 'http://kernel.org/pub/software/scm/git', 'tar.gz'),
            ('sqlite-amalgamation', '3.6.17', 'http://www.sqlite.org', 'tar.gz'),
        ]
        self.frontendDeps = [
            'openssh', 'ruby', 'gcc', 'gcc-c++', 'zlib-devel', 'mkisofs', 'curl'
        ]
        self.nodeDeps = ['ruby', 'curl', 'libvirt', 'mkisofs', 'openssh', 'brctl']
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
        
        self.packages = {'apache2': PackageInfo('httpd','/etc/httpd')}
        
        super(CentOS, self).__init__()

    def getSystemArch(self):
        _, _, _, _, arch = os.uname()

        if arch == 'x86_64':
            return arch
        else:
            return 'i386' 

    # -------------------------------------------
    #     Package manager and related
    # -------------------------------------------

    def updatePackageManager(self):
        pass

    def installPackages(self, packages):
        if len(packages) < 1:
            return

        cmd = self.installCmd.split(' ')
        cmd.extend(packages)
        self._execute(cmd)

    def installNodePackages(self, packages):
        if len(packages) > 0:
            self._nodeShell('%s %s' % 
                            (self.installCmd, ' '.join(packages)))

    def installFrontendDependencies(self):
        super(CentOS, self).installFrontendDependencies()
        self.installRemotePackages(self.remotePackagesAddress(self.remotePackages))
        self.installSourceDependencies(self.remoteSourcesAddress(self.remoteSources))

    def remotePackagesAddress(self, packages):
        remotePackages = []
        
        for name, version, arch, uri in packages:
            remotePackages.append('%s/%s-%s.%s.rpm' % (uri % ({'arch': arch}), name, version, arch))
        
        return remotePackages
    
    def installRemotePackages(self, packages):
        rpmName = '/tmp/stratus-%d.rpm'
        pkgList = []

        for i in range(len(packages)):
            pkg = packages.pop()
            wget(pkg, rpmName % i)
            pkgList.append(rpmName % i)

        self.installPackages(pkgList)

    # -------------------------------------------
    #     Source build and installation methods
    # -------------------------------------------
        
    def remoteSourcesAddress(self, sources):
        remoteSources = []
        
        for name, version, uri, ext in sources:
            remoteSources.append('%s/%s-%s.%s' % (uri, name, version, ext))
            
        return remoteSources
    
    def installSourceDependencies(self, sourcesAddress):
        for dep in sourcesAddress:
            self.buildAndInstall(dep)
    
    def buildAndInstall(self, sourceAddr):
        archive = '/tmp/stratus-deps-src.tar.gz'
        wget(sourceAddr, archive)
        tar = tarfile.open(archive)
        srcFile = tar.getmembers()

        for elem in srcFile:
            tar.extract(elem)

        os.chdir(srcFile[0].name)
        self._execute(['./configure'])
        self._execute(['make', '-j2', 'install'])
        os.chdir('../')
        
    # -------------------------------------------
    #     File sharing related methods
    # -------------------------------------------
        
    def configureNewNfsServer(self, mountPoint, networkAddr, networkMask):
        super(CentOS, self).configureNewNfsServer(mountPoint, networkAddr, networkMask)
        self._execute(['service', 'nfs', 'start'])
        
    # -------------------------------------------
    #     Hypervisor related methods
    # -------------------------------------------

    def _configureKvm(self):
        super(CentOS, self)._configureKvm()
        self.executeCmd(['/etc/init.d/libvirtd start'])
        self.executeCmd(['usermod', '-G', 'kvm', '-a', self.ONeAdmin])
        self.executeCmd(['chown', 'root:kvm', 
                        '/var/run/libvirt/libvirt-sock'])
        self.executeCmd(['chmod', 'g+r+w', '/var/run/libvirt/libvirt-sock'])
        self.executeCmd(['ln', '-fs', '/usr/bin/qemu', '/usr/bin/kvm'])
        
    # -------------------------------------------
    #     Network configuration and related
    # -------------------------------------------
        
    def configureNetwork(self, networkInterface, bridge):
        self.filePutContentsCmd('/etc/sysconfig/network-scripts/ifcfg-%s' % networkInterface,
                'DEVICE=%s\nTYPE=Ethernet\nBRIDGE=%s\n' % (networkInterface, bridge))
        self.filePutContentsCmd('/etc/sysconfig/network-scripts/ifcfg-%s' % bridge,
                'DEVICE=%s\nBOOTPROTO=dhcp\nONBOOT=yes\nTYPE=Bridge' % bridge)
        self.executeCmd(['/etc/init.d/network restart'])

system = CentOS()
