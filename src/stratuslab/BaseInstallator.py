from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import getSystemMethods
from stratuslab.Util import printAction
from stratuslab.Util import printStep

class BaseInstallator(object):
    
    def __init__(self):
        # Default network added automatically at installation
        # Make sure one_%(name)s_* exist in the config 
        self.defaultNetworks = ['private', 'public']
        
        self.config = None
        self.options = {}
        self.nodeAddr = None
        self.shareType = None
        self.frontend = None
        self.node = None

    def runInstall(self, options, config):
        self.config = config
        self.nodeAddr = options.nodeAddr
        self.shareType = self.config.get('share_type')
        
        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(self.config.get('one_username'),
                                  self.config.get('one_password'))


        # TODO: Automatically determine system
        self.frontend = getSystemMethods(self.config.get('frontend_system'), options.__dict__)
        self.node = getSystemMethods(self.config.get('node_system'), options.__dict__)

        if self.nodeAddr:
            printAction('Starting node installation')
            self.runInstallNodes()
        else:
            printAction('Starting frontend installation')
            self.runInstallFrontend()
            
        printAction('Installation completed')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (self.frontend.stdout.name, 
                                                                        self.frontend.stderr.name)
          
    def runInstallNodes(self):
        self.propagateNodeInfos()

        printStep('Checking node connectivity')
        if not self.nodeAlive():
            raise ValueError('Unable to connect the node %s' % self.nodeAddr)

        printStep('Creating cloud admin account')
        self.createCloudAdmin(self.node)
        
        printStep('Configuring cloud admin account')
        self.configureCloudAdminNode()
        
        printStep('Installing dependencies')
        self.installNodeDependencies()
        
        printStep('Configuring file sharing')
        self.setupFileSharingClient()
        
        printStep('Adding node to cloud')
        self.addCloudNode()
        
        if self.config.get('hypervisor') == 'xen':
            print '\n\tPlease reboot the node on the Xen kernel to complete the installation'

    def runInstallFrontend(self):
        printStep('Configuring file sharing')
        self.setupFileSharingServer()

        printStep('Creating cloud admin account')
        self.createCloudAdmin(self.frontend)
        
        printStep('Configuring cloud admin account')
        self.configureCloudAdminFrontend()
        
        printStep('Installing cloud system')
        self.installCloudSystem()
        
        printStep('Configuring cloud system')
        self.configureCloudSystem()
        
        printStep('Starting cloud')
        self.startCloudSystem()
        
        printStep('Adding default networks')
        self.addDefaultNetworks()

    def propagateNodeInfos(self):
        self.node.setNodeAddr(self.nodeAddr)
        self.node.setNodePrivateKey(self.privateKey)
        self.node.setNodePort(self.config.get('node_ssh_port'))
        self.node.setNodeHypervisor(self.config.get('hypervisor'))
        self.node.workOnNode()
        self.frontend.setCloudAdminName(self.config.get('one_username'))
        
    def nodeAlive(self):
        return self.node._nodeShell('exit 42') == 42
    
    def startCloudSystem(self):
        self.frontend.startCloudSystem()

    def installNodeDependencies(self):
        self.node.installNodeDependencies()
        self.node.installHypervisor()
        self.node.configureHypervisor()

    def createCloudAdmin(self, system):
        pass
    
    def configureCloudAdminNode(self):
        pass
    
    def installCloudSystem(self):
        pass
    
    def setupFileSharingClient(self):
        pass
    
    def addCloudNode(self):
        pass
    
    def configureCloudAdminFrontend(self):
        pass
    
    def configureCloudSystem(self):
        pass
    
    def addDefaultNetworks(self):
        pass

    def assignKey(self, options, config):
        self.privateKey = (True and options.privateKey) or (config.get('node_private_key'))
    
    def assignDrivers(self, options, config):
        self.infoDriver = (True and options.infoDriver) or ('im_%s' % config.get('hypervisor'))
        self.virtDriver = (True and options.virtDriver) or ('vmm_%s' % config.get('hypervisor'))
        self.transfertDriver = (True and options.transfertDriver) or ('tm_%s' % config.get('share_type'))
