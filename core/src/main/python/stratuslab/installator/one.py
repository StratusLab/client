import os

from BaseInstallator import BaseInstallator
from stratuslab.Util import fileGetContent
from stratuslab.Util import networkSizeToNetmask
from stratuslab.Util import unifyNetsize
import stratuslab.Util as Util

class OneInstallator(BaseInstallator):
    
    def __init__(self):
        super(OneInstallator, self).__init__()
        self.cloudConfDir = '/etc/one/'
        self.cloudConfFile = self.cloudConfDir + 'oned.conf'

    def _addCloudNode(self):
        return self.cloud.hostCreate(self.nodeAddr, self.infoDriver, self.virtDriver, self.transfertDriver)
        
    def _removeCloudNode(self, id):
        self.cloud.hostRemove(id)
        
    def _addDefaultNetworks(self):
        for vnet in self.defaultNetworks:
            if self._isIpMacNetwork(vnet):
                self.cloud.networkCreate(self._buildFixedMacIpNetworkTemplate(vnet))
            elif self._isRangedNetwork(vnet):
                self.cloud.networkCreate(self._buildRangedNetworkTemplate(vnet))
            else:
                self.cloud.networkCreate(self._buildFixedNetworkTemplate(vnet))
        self._addPrivateNetworkRoute(self.frontend)

    def _isIpMacNetwork(self, vnet):
        addrDefined = self.config.get('one_%s_network_addr' % vnet, '') != ''
        macDefined = self.config.get('one_%s_network_mac' % vnet, '') != ''
        return addrDefined and macDefined

    def _isRangedNetwork(self, vnet):
        addrDefined = self.config.get('one_%s_network_addr' % vnet, '') != ''
        return addrDefined

    def _buildFixedMacIpNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(Util.shareDir + 'vnet/fixed.net')
        
        ips = self.config.get('one_%s_network_addr' % networkName).split(' ')
        macs = self.config.get('one_%s_network_mac' % networkName).split(' ')
        ipMac = zip(ips, macs)
        
        leases = ['LEASES = [ IP=%s, MAC=%s]' % (ip, mac) for ip, mac in ipMac]
        
        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'leases': '\n'.join(leases)})
        return vnetTpl
    
    def _buildFixedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(Util.shareDir + 'vnet/fixed.net')
        
        leases = ['LEASES = [ IP="%s"]' % i for i in self.config.get('one_%s_network_addr' % networkName).split(' ')]
        
        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'leases': '\n'.join(leases)})
        return vnetTpl
    
    def _buildRangedNetworkTemplate(self, networkName):
        vnetTpl = fileGetContent(Util.shareDir + 'vnet/ranged.net')
        vnetTpl = vnetTpl % ({'network_name': networkName,
                             'bridge': self.config.get('node_bridge_name'),
                             'network_size': self.config.get('one_%s_network_size' % networkName),
                             'network_addr': self.config.get('one_%s_network' % networkName)})
        return vnetTpl

    def _addPrivateNetworkRoute(self, system):
        routesTmp = '/tmp/stratus-route.tmp'
        routesFd = open(routesTmp, 'wb')
        system.executeCmd(['route', '-n'], stdout=routesFd)
        routesFd.close()

        routesFd = open(routesTmp, 'rb')
        routes = routesFd.readlines()
        routesFd.close()
        os.remove(routesTmp)

        addRoute = True
        for line in routes:
            if line.startswith(self.config.get('one_private_network')):
                addRoute = False
                break

        if addRoute:
            system.executeCmd(['route', 'add', '-net',
                '%s/%s' % (self.config.get('one_private_network'),
                networkSizeToNetmask(unifyNetsize(self.config.get('one_private_network_size')))),
                'dev', 'eth0'])

    def _copyContextualizationScript(self):
        self.frontend.createDirsCmd(os.path.dirname(self.contextScript))
        self.frontend.setOwnerCmd(os.path.dirname(self.contextScript))
        self.frontend.copyCmd(os.path.join(Util.shareDir, 'context/init.sh'), self.contextScript)
        self.frontend.setOwnerCmd(self.contextScript)

    def _copyCloudHooks(self, system):
        hooksDir = '%s/share/hooks' % self.config.get('one_share')
        hooksInstallDir = os.path.join(Util.shareDir + 'hooks')
        system.createDirsCmd(hooksDir)
        system.setOwnerCmd(hooksDir)
        
        for file in os.listdir(hooksInstallDir):
            system.copyCmd('%s/%s' % (hooksInstallDir, file), hooksDir)
            system.setOwnerCmd('%s/%s' % (hooksDir, file))
            system.chmodCmd('%s/%s' % (hooksDir, file), 0755)

    # -------------------------------------------
    #   Front-end file sharing management
    # -------------------------------------------
    
    def _setupFileSharingServer(self):
        self.frontend.installPackages(self.frontend.fileSharingFrontendDeps.get(self.shareType, []))
        self._configureFileSharingServer()

    def _configureFileSharingServer(self):
        if self.shareType == 'nfs':
            self._configureNfsServer()
        elif self.shareType == 'ssh':
            self.frontend.configureSshServer()

    # ---- NFS configuration

    def _configureNfsServer(self):
        if self._nfsShareAlreadyExists():
            if self.config.get('vm_dir') != '':
                mountPoint = self.config.get('vm_dir')
            else:
                mountPoint = os.path.dirname(self.config.get('one_home'))

            self.frontend.configureExistingNfsShare(self.config.get('existing_nfs'), mountPoint)
        else:
            if self.config.get('vm_dir') != '':
                mountPoint = self.config.get('vm_dir')
            else:
                mountPoint = '%s/var' % self.config.get('one_home')

            self.frontend.configureNewNfsServer(mountPoint,
                                                self.config['network_addr'],
                                                self.config['network_mask'])

    def _nfsShareAlreadyExists(self):
        return not (self.config.get('existing_nfs', '') == '')
    
    # -------------------------------------------
    #    Node file sharing management
    # -------------------------------------------

    def _setupFileSharingClient(self):
        self.node.installNodePackages(self.node.fileSharingNodeDeps.get(self.shareType, []))
        self._configureFileSharingClient()

    def _configureFileSharingClient(self):
        if self.shareType == 'nfs':
            self._configureNfsClient()
        elif self.shareType == 'ssh':
            self.node.configureSshClient(self.config.get('vm_dir'))
    
    # ---- NFS configuration   
         
    def _configureNfsClient(self):
        if self._nfsShareAlreadyExists():
            if self.config.get('vm_dir') != '':
                host = self.config.get('existing_nfs')
                mountPoint = self.config.get('vm_dir')
            else:
                host = '%s/%s/var' % (self.config.get('existing_nfs'),
                                  os.path.basename(self.config.get('one_home')))
                mountPoint = '%s/var' % self.config.get('one_home')
        else:
            if self.config.get('vm_dir') != '':
                host = '%s:%s' % (self.config['frontend_ip'], self.config.get('vm_dir'))
                mountPoint = self.config.get('vm_dir')
            else:
                host = '%s:%s/var' % (self.config['frontend_ip'], self.config.get('one_home'))
                mountPoint = '%s/var' % self.config.get('one_home')

        self.node.configureExistingNfsShare(host, mountPoint)
