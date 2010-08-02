import os
import shutil
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import fileGetContent
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import waitUntilPingOrTimeout

class Creator(object):
    
    def __init__(self, config, options, stockImg):
        self.config = config
        self.options = options
        self.stockImg = stockImg
        
        self.imageName = os.path.basename(self.stockImg)
        self.imagePath = '%s/%s' % (self.options.destination,
                                    self.imageName)
        self.manifest = '%s.manifest.xml' % self.imageName
        
        cloudFactory = CloudConnectorFactory()
        self.cloud = cloudFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(self.config.get('one_username'),
                                  self.config.get('one_password'))
        
        # Attributes initialization
        self.vmTemplate = None
        self.vmId = None
        self.vmAddress = None
        
    def createMachineTemplate(self, template):
        self.vmTemplate = fileGetContent(template) % ({'vm_image': self.imagePath,
                                                      'vm_name': self.imageName})

    def addPublicInterface(self):
        # We assume the is a public network
        self.vmTemplate += '\nNIC = [ NETWORK = "public" ]\n'
        
    def duplicateStockImage(self):
        shutil.copy(self.stockImg, self.options.destination)
        
    def create(self):
        printAction('Starting image creation')
        
        printStep('Copying stock image')
        self.duplicateStockImage()

        printStep('Creating machine template')
        self.createMachineTemplate(self.options.oneTpl)
        
        if not self.options.shutdownVm:
            self.addPublicInterface(self.vmTemplate)

        printStep('Booting new machine')
        self.vmId = self.cloud.vmStart(self.vmTemplate)
        
        if not self.cloud.waitUntilVmRunningOrTimeout(self.vmId, 20):
            printError('Unable to boot VM')

        printStep('Waiting for network interface to be up')
        self.vmAddress = self.cloud.getVmIp(self.vmId).get('private')
        
        if not waitUntilPingOrTimeout(self.vmAddress, 20):
            self.cloud.vmStop(self.vmId)
            printError('Unable to ping VM')
            
        printStep('Populating machine manifest')

        printStep('Installing ONE contextualisation mechanism')

        printStep('Installing user packages')

        printStep('Executing user scripts')

        if self.options.shutdownVm:
            printStep('Shutting down machine')
            self.cloud.vmStop(self.vmId)
        else:
            printStep('Machine ready for your usage')
            publicAddress = self.cloud.getVmIp(self.vmId).get('public', 'No public address')
            print '\n\tMachine IP: %s' % publicAddress
            print '\tRemember to stop the machine when finished'
            
        printAction('Image creation finished')
        print '\n\tManifest: %s' % self.manifest
            