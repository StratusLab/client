from stratuslab.BaseSystem import BaseSystem

class Ubuntu(BaseSystem):

    def __init__(self):
        self.systemName = 'Ubuntu 10.04'
        self.installCmd = 'apt-get -q -y install' 
        self.frontendDeps = [
            'ruby', 'libsqlite3-dev', 'libxmlrpc-c3-dev', 'libssl-dev',
            'scons', 'g++', 'git-core', 'ssh', 'libvirt-bin'
        ]
        self.nodeDeps = ['ruby']
        self.hypervisorDeps = {
            'xen': ['xen-hypervisor-3.3'],
            'kvm': ['qemu-kvm'],
        }
        self.fileSharingFrontendDeps = {
            'nfs': ['nfs-kernel-server'],
            'ssh': [],
        }
        self.fileSharingNodeDeps = {
            'nfs': ['nfs-common'],
            'ssh': [],
        }
        super(Ubuntu, self).__init__()

    def updatePackageManager(self):
        self.execute(['apt-get', 'update'])

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
            
    def createONeAdmin(self, username, uid, homeDir, password):
        super(Ubuntu, self).createONeAdmin(username, uid, homeDir, password)
        self.configureLibvirt()

    def configureLibvirt(self):
        self.executeCmd(['usermod', '-G', 'libvirtd', '-a', self.ONeAdmin])

system = Ubuntu()

