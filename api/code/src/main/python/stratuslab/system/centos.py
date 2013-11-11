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
import tarfile

from BaseSystem import BaseSystem
from stratuslab.system.PackageInfo import PackageInfo
import stratuslab.Util as Util
from stratuslab import Exceptions
import re

packageManagerReposConfDir = '/etc/yum.repos.d'
installCmd = 'yum -y --nogpgcheck install'
updateCmd = 'yum -y update'
cleanPackageCacheCmd = 'yum clean all'
queryPackageCmd = 'rpm -q'

repoFileNamePattern = '%s/%s.repo' %(packageManagerReposConfDir, '%s')

class CentOS(BaseSystem):

    os = 'centos'

    def __init__(self):
        super(CentOS, self).__init__()
        
        self.repoFileNamePattern = repoFileNamePattern
        
        self.systemName = 'CentOS 5.5'
        self.arch = self.getSystemArch()
        self.installCmd = installCmd
        self.remotePackages = [
            # ('name', 'version', 'arch', 'uri')
            # --> <uri>/<name>-<version>.<arch>.rpm
            ('scons', '1.2.0-1', 'noarch', 'http://prdownloads.sourceforge.net/scons'),
            ('xmlrpc-c', '1.06.18-1.el5.kb', self.arch, 'http://centos.karan.org/el5/extras/testing/%(arch)s/RPMS'),
            ('xmlrpc-c-devel', '1.06.18-1.el5.kb', self.arch, 'http://centos.karan.org/el5/extras/testing/%(arch)s/RPMS'),
        ]
#        self.remoteSources = [
#            # ('name', 'version', 'uri', 'extension')
#            # --> <uri>/<name>-<version>.<extention>
#            ('git', '1.7.1.1', 'http://kernel.org/pub/software/scm/git', 'tar.gz'),
#            ('sqlite-amalgamation', '3.6.17', 'http://www.sqlite.org', 'tar.gz'),
#        ]
        self.frontendDeps = [
            'openssh', 'ruby', 'gcc', 'gcc-c++', 'zlib-devel', 'genisoimage', 'curl'
        ]
        self.nodeDeps = ['ruby', 'curl', 'libvirt', 'genisoimage', 'openssh', 'bridge-utils',
                         'stratuslab-vmusage']
        self.hypervisorDeps = {
            'xen': ['xen', 'kernel-xen'],
            'kvm': ['qemu-kvm'],
        }
        self.fileSharingFrontendDeps = {
            'nfs': [],
            'ssh': [],
        }
        self.fileSharingNodeDeps = {
            'nfs': [],
            'ssh': [],
        }

        self.extraRepos = {
            'epel' : {'content' : """[epel]
name=Extra Packages for Enterprise Linux 6 - $basearch
#baseurl=http://download.fedoraproject.org/pub/epel/6/$basearch
mirrorlist=https://mirrors.fedoraproject.org/metalink?repo=epel-6&arch=$basearch
failovermethod=priority
enabled=1
gpgcheck=0
#gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-6
""", 'filename' : repoFileNamePattern % 'epel'},

            self.caRepoName : {'content' : """[EGI-trustanchors]
name=EGI-trustanchors
baseurl=http://repository.egi.eu/sw/production/cas/1/current/
#gpgkey=http://repository.egi.eu/sw/production/cas/1/GPG-KEY-EUGridPMA-RPM-3
gpgcheck=0
enabled=1
""", 'filename' : repoFileNamePattern % self.caRepoName}
            }

        self.packages.update({'apache2': PackageInfo('httpd','/etc/httpd'),
                         'dhcp': PackageInfo('dhcp',
                                             configFile='/etc/dhcp/dhcpd.conf',
                                             initdScriptName='dhcpd'),
                         'CA' : PackageInfo('ca-policy-egi-core', 
                                                repository=self.caRepoName),
                         'MySQLServer': PackageInfo('mysql-server',
                                                    initdScriptName='mysqld'),
                         'fetch-crl': PackageInfo('fetch-crl',
                                                  packageVersion='3*'),
                         'sendmail': PackageInfo('sendmail')})

        self.installPackagesErrorMsgs = ['No package .* available']


    def getSystemArch(self):
        try:
            _, _, _, _, arch = os.uname()
            if arch == 'x86_64':
                return arch
            else:
                return 'i386'
        except AttributeError:
            return 'i386'

    # -------------------------------------------
    #     Package manager and related
    # -------------------------------------------
    
    def addRepositories(self, packages):
        """Accepts package names and aliases as defined in self.packages.
        """
        repos = []
        for pkgName in packages:
            repo = ''
            if pkgName in self.packages:
                repo = self.packages[pkgName].repository
            else:
                for pkgInfo in self.packages.values():
                    if pkgInfo.packageName == pkgName:
                        repo = pkgInfo.repository
            if repo and repo not in repos:
                repos.append(repo)
        
        for repo in repos:
            if repo in self.extraRepos:
                filename = self.extraRepos[repo]['filename']
                content = self.extraRepos[repo]['content']
                Util.filePutContent(filename, content)
            else:
                Util.printError("Repository '%s' is not defined in the extra list of repositories (%s)." % \
                                (repo, ', '.join(self.extraRepos)))

    def updatePackageManager(self):
        pass

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
            Util.wget(pkg, rpmName % i)
            pkgList.append(rpmName % i)

        self.installPackages(pkgList)

    def getIsPackageInstalledCommand(self, package):
        cmd = '%s %s' % (queryPackageCmd, package)
        return cmd

    def enableServiceOnBoot(self, service, level='3'):
        cmd = ['chkconfig', '--level', str(level), service, 'on']
        rc, output = self._executeWithOutput(cmd)
        if rc != 0:
            Util.printDetail(output)
        return rc

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
        Util.wget(sourceAddr, archive)
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
        self.executeCmd(['service', 'nfs', 'start'])

    # -------------------------------------------
    #     Hypervisor related methods
    # -------------------------------------------

    def _configureKvm(self):
        super(CentOS, self)._configureKvm()
        self.executeCmd(['/etc/init.d/libvirtd start'])
        # Sleep to give a chance to libvirt to create the libvirt-sock
        Util.sleep(5)
        self.executeCmd(['usermod', '-G', 'kvm', '-a', self.oneUsername])
        self.executeCmd(['chown', 'root:kvm',
                        '/var/run/libvirt/libvirt-sock'])
        self.executeCmd(['chmod', 'g+r+w', '/var/run/libvirt/libvirt-sock'])

        self.executeCmd('ln -s /usr/libexec/qemu-kvm /usr/bin/qemu-kvm'.split())

    # -------------------------------------------
    # Network related methods
    # -------------------------------------------

    def _configureNetworkInterface(self, device, ip, netmask):
        deviceConf = '/etc/sysconfig/network-scripts/ifcfg-%s' % device
        data = """DEVICE=%s
IPADDR=%s
NETMASK=%s
""" % (device, ip, netmask)
        Util.filePutContent(deviceConf, data)

    def _persistRemoteBridgeConfig(self, iface, bridge):
        netScriptsDir = '/etc/sysconfig/network-scripts/'
        ifaceFile = '%s/ifcfg-%s' % (netScriptsDir, iface)
        bridgeFile = '%s/ifcfg-%s' % (netScriptsDir, bridge)

        if self._nodeShell('[ -f %s ]' % bridgeFile, shell=True) == 0:
            Util.printWarning(('Bridge configuration already present (%s:%s).' % 
                               (self.nodeAddr, bridgeFile)) + \
                               ' Please update it manually if required.')
            return

        cmd = 'cat %s' % ifaceFile
        rc, output = self._nodeShell(cmd, withOutput=True, shell=True)
        if rc != 0:
            Util.printWarning('Failed to get content of %s:%s:\n%s' % 
                              (self.nodeAddr, ifaceFile, output))
            return

        ifaceConfOrig = output
        try:
            bridgeConf, ifaceConf = self._buildBridgeAndIfaceConfig(ifaceConfOrig,
                                                                    iface, bridge)
        except Exceptions.ConfigurationException, ex:
            Util.printWarning('Failed to build config for %s and %s.\n%s' % 
                              (iface, bridge, str(ex)))
            return
        else:
            self._writeToFilesRemote([(bridgeFile, bridgeConf), (ifaceFile, ifaceConf)])

    @staticmethod
    def _buildBridgeAndIfaceConfig(ifaceConfOrig, iface, bridge):
        
        res = re.search('(^BOOTPROTO.*)', ifaceConfOrig, re.M)
        if not res:
            raise Exceptions.ConfigurationException('BOOTPROTO not defined in %s config.' % iface)
        else:
            BOOTPROTO = res.group()

        bridgeConf = """DEVICE=%s
TYPE=Bridge
ONBOOT=yes
DELAY=0
IPV6INIT=yes
""" % bridge
        
        BOOTPROTO = BOOTPROTO.split('=')[1]
        if BOOTPROTO == 'static':
            # copy static conf from main interface
            bridgeConf += "BOOTPROTO=static\n"
            pat = '.*|'.join(['BROADCAST', 'IPADDR', 'NETMASK', 
                              'NETWORK', 'GATEWAY']) + '.*'
            matches = re.findall('^(%s)' % pat, ifaceConfOrig, re.M)
            for match in matches:
                bridgeConf += '%s\n' % match
        else:
            bridgeConf += "BOOTPROTO=%s\n" % BOOTPROTO

        ifaceConf = """DEVICE=%s
ONBOOT=yes
BRIDGE=%s
""" % (iface, bridge)

        for key in ['IPV6INIT', 'HWADDR']:
            res = re.search('(^%s.*)' % key, ifaceConfOrig, re.M)
            if res:
                ifaceConf += '%s\n' % res.group()
        
        return bridgeConf, ifaceConf


    # -------------------------------------------
    # Security
    # -------------------------------------------
        
    def _enableFetchCrl(self):

        Util.printDetail('Enabling fetch-crl-cron.')
        self.startService('fetch-crl-cron')
        self.enableServiceOnBoot('fetch-crl-cron', '3')


system = CentOS()
