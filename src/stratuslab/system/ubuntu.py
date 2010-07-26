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

    # -------------------------------------------
    #     Package manager and related
    # -------------------------------------------

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
            
    # -------------------------------------------
    #     Hypervisor related methods
    # -------------------------------------------
            
    def configureKVM(self):
        self.executeCmd(['usermod', '-G', 'libvirtd', '-a', self.ONeAdmin])
        
    # -------------------------------------------
    #     Network configuration and related
    # -------------------------------------------
        
    def configureNetwork(self, networkInterface, bridge):
        self.executeCmd(['sed \'s/.*%s.*/#&/\'' % networkInterface])
        self.filePutContentsCmd('/etc/network/interfaces',
            'auto %(bridge)s\n'
            'iface %(bridge)s inet dhcp\n'
            'pre-up ifconfig %(iface)s down\n'
            'pre-up brctl addbr %(bridge)s\n'
            'pre-up brctl addif %(bridge)s %(iface)s\n'
            'pre-up ifconfig %(iface)s 0.0.0.0\n'
            'post-down ifconfig %(iface)s down\n'
            'post-down ifconfig %(bridge)s down\n'
            'post-down brctl delif %(bridge)s %(iface)s\n'
            'post-down brctl delbr %(bridge)s\n'
            % ({'bridge': bridge, 'iface': networkInterface}))

system = Ubuntu()

