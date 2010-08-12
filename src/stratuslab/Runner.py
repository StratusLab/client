import os.path
import sys

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import fileGetContent
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import validateIp

class Runner(object):

    def __init__(self, image, options, config):
        self.image = image
        self.config = config
        self.instanceNumber = options.instanceNumber
        self.instanceType = options.instanceType
        self.userKey = options.userKey
        self.vmTemplatePath = options.vmTemplate
        self.extraNic = options.extraNic
        self.rawData = options.rawData
        self.vmKernel = options.vmKernel
        self.vmRamdisk = options.vmRamdisk
        self.addressing = options.addressing
        self.extraContextFile = options.extraContext
        self.extraContext = ''

        self.defaultVmNic = ['public', 'private']

        # Will contain the NIC string 
        self.vmNic = ''
        self.nicIpContext = 'ip_public = "$NIC[IP, NETWORK=\"public\"]",\n'

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'), 
                               self.config.get('one_port'))
        self.cloud.setCredentials(options.username, options.password)

        self.osOptions = ''

    @staticmethod
    def getInstanceType():
        types = {
            # name      :   (cpu, ram, swap)
            'm1.small'  :   (1, 128, 1024),
            'c1.medium' :   (1, 256, 1024),
            'm1.large'  :   (2, 512, 1024),
            'm1.xlarge' :   (2, 1024, 1024),
            'c1.xlarge' :   (4, 2048, 2048),
        }
        return types

    def _populateTemplate(self, template):
        # TODO: Additional NIC are not set for the moment by the init script. Need a way to do it
        
        vmTemplate = fileGetContent(template)
        cpu, ram, swap = self.getInstanceType().get(self.instanceType)

        self._formatOsOptions()
        self._formatNicList()
        self._formatRawData()
        self._formatExtraContext()

        vmTemplate = vmTemplate % {
            'vm_cpu': cpu,
            'vm_ram': ram,
            'vm_swap': swap,
            'vm_image': self.image,
            'os_options': self.osOptions,
            'vm_nic': self.vmNic,
            'raw_data': self.rawData,
            'user_key_path': self.userKey,
            'user_key_name': os.path.basename(self.userKey),
            'one_home': self.config.get('one_home'),
            'extra_context': self.extraContext,
            'nic_ip': self.nicIpContext,
        }

        return vmTemplate

    def _formatOsOptions(self):
        if self.vmKernel or self.vmRamdisk:
            self.osOptions = 'OS = ['

            if self.vmKernel:
                self.osOptions += '\nkernel = "%s",' % self.vmKernel

            if self.vmRamdisk:
                self.osOptions += '\ninitrd = "%s",' % self.vmRamdisk

            self.osOptions += '\n]'

    def _formatNicList(self):
        if validateIp(self.addressing):
            self.vmNic += 'NIC = [ network = "public", ip = "%s" ]\n' % self.addressing
            self.defaultVmNic.remove('public')

        if self.addressing == 'private':
            self.defaultVmNic.remove('public')
            self.nicIpContext = ''

        if self.extraNic:
            self.defaultVmNic.append(self.extraNic)
            self.nicIpContext += 'ip_extra = "$NIC[IP, NETWORK=\"%s\"]",\n' % self.extraNic

        for nic in self.defaultVmNic:
            self.vmNic += 'NIC = [ network = "%s" ]\n' % nic

    def _formatRawData(self):
        if self.rawData:
            self.rawData = 'RAW = [ type="%s", data="%s" ]' % (self.config.get('hypervisor'),
                                                               self.rawData)

    def _formatExtraContext(self):
        if not self.extraContextFile:
            return
        
        extraContext = open(self.extraContextFile, 'rb')
        self.extraContext = ',\n'.join(extraContext.read().split('\n'))
        extraContext.close()

    def runInstance(self):
        vmTpl = self._populateTemplate(self.vmTemplatePath)

        plurial = { True: 'machines',
                    False: 'machine' }

        printAction('Starting %s %s' % (self.instanceNumber,
                                        plurial.get(self.instanceNumber > 1)))

        for i in range(self.instanceNumber):
            try:
                vmId = self.cloud.vmStart(vmTpl)
            except Exception, e:
                printError(e)
                
            vmIp = self.cloud.getVmIp(vmId).get('public', 'No public IP')
            printStep('VM %s: %s' % (vmId, vmIp))

        printAction('Done!')
        