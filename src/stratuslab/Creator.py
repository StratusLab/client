import os
import shutil
import subprocess
from datetime import datetime

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import getSystemMethods
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
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
#        self.cloud = cloudFactory.getCloud()
        self.cloud = cloudFactory.getDummyCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
#        self.cloud.setCredentials(self.config.get('one_username'),
        self.cloud.setCredentials(self.config.get('node_private_key'),
                                  self.config.get('one_password'))

        self.sshKey = self.config.get('node_private_key')

        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')
        
        # Attributes initialization
        self.vmTemplate = None
        self.vmId = None
        self.vmAddress = None
        self.publicAddress = None
        self.vmSshPort = None
        self.system = None
        
    def _createMachineTemplate(self, template):
        pass
        #self.vmTemplate = fileGetContent(template) % ({'vm_image': self.imagePath,
        #                                              'vm_name': self.imageName})

    def _addPublicInterface(self):
        pass
        # We assume the is a public network
        #self.vmTemplate += '\nNIC = [ NETWORK = "public" ]\n'
        
    def _duplicateStockImage(self):
        # TODO: Handle remote (http) images
        # TODO: Handle compressed images
        shutil.copy(self.stockImg, self.options.destination)

    def _populateManifest(self):
        system = self._getVmSystem()
        self.system = getSystemMethods(system)
        
        arch = self._getVmArch()

    def _getVmSystem(self):
        uname = sshCmd('uname -a', self.vmAddress, self.sshKey, self.vmSshPort,
                                noWait=True, stdout=subprocess.PIPE).communicate()[0]

        # Very simple determination for the moment as we don't support many distro
        system = 'unknow'
        if uname.find('Ubuntu') != -1:
            system = 'ubuntu'
        elif uname.find('el5') != -1:
            system = 'centos'

        return system

    def _getVmArch(self):
        return sshCmd('uname -m', self.vmAddress, self.sshKey, self.vmSshPort,
                                noWait=True, stdout=subprocess.PIPE).communicate()[0]

    def _installPackages(self):
        if len(self.options.packages) == 0:
            return
        
        ret = sshCmd('%s %s' % (self.system.installCmd, self.options.packages),
                        self.vmAddress, self.sshKey, self.vmSshPort,
                        stderr=self.stderr, stdout=self.stdout)

        if ret != 0:
            printError('An error occured while installing packages')

    def _executeScripts(self):
        if len(self.options.scripts) == 0:
            return

        for script in self.options.scripts.split(' '):
            scp(script, 'root@%s:' % self.vmAddress, self.sshKey, self.vmSshPort,
                    stderr=self.stderr, stdout=self.stdout)

            ret = sshCmd('bash %s' % script, self.vmAddress, self.sshKey, self.vmSshPort,
                        stderr=self.stderr, stdout=self.stdout)
            sshCmd('rm -fr %s' % script, self.vmAddress, self.sshKey, self.vmSshPort)

            if ret != 0:
                printError('An error occured while executing script %s' % script)

    def create(self):
        printAction('Starting image creation')
        
        printStep('Copying stock image')
        #self._duplicateStockImage()

        printStep('Creating machine template')
        self._createMachineTemplate(self.options.oneTpl)
        
        if not self.options.shutdownVm:
            self._addPublicInterface()

        printStep('Booting new machine')
#        self.vmId = self.cloud.vmStart(self.vmTemplate)
        self.vmId = self.cloud.vmStart(self.imagePath)
        
        if not self.cloud.waitUntilVmRunningOrTimeout(self.vmId, 60):
            printError('Unable to boot VM')

        printStep('Waiting for network interface to be up')
        self.vmAddress = self.cloud.getVmIp(self.vmId).get('private')
        self.publicAddress = self.cloud.getVmIp(self.vmId).get('public', 'No public address')
        self.vmSshPort = self.cloud.getVmSshPort(self.vmId)
        
        if not waitUntilPingOrTimeout(self.vmAddress, 20):
            self.cloud.vmStop(self.vmId)
            printError('Unable to ping VM')
            
        printStep('Populating machine manifest')
        self._populateManifest()

        printStep('Installing ONE contextualisation mechanism')

        printStep('Installing user packages')
        self._installPackages()

        printStep('Executing user scripts')
        self._executeScripts()

        if self.options.shutdownVm:
            printStep('Shutting down machine')
            self.cloud.vmStop(self.vmId)
        else:
            printStep('Machine ready for your usage')
            print '\n\tMachine IP: %s' % self.publicAddress
            print '\tRemember to stop the machine when finished',
            
        printAction('Image creation finished')
        print '\n\tManifest: %s' % self.manifest,
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (self.stdout.name,
                                                                        self.stderr.name)
            