import os

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import cliLineSplitChar
from stratuslab.Util import fileGetContent
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import validateIp

class Runner(object):

    def __init__(self, image, options, config):
        self.config = config
        self.instanceNumber = options.instanceNumber
        self.instanceType = options.instanceType
        self.vmTemplatePath = options.vmTemplate
        self.extraNic = options.extraNic
        self.rawData = options.rawData
        self.vmKernel = options.vmKernel
        self.vmRamdisk = options.vmRamdisk
        self.addressing = options.addressing
        self.extraContextFile = options.extraContextFile
        self.extraContextData = options.extraContext

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(options.username, options.password)

        # NIC which are set by default
        self.defaultVmNic = ['public', 'private']

        # VM template parameters initialization
        self.vm_cpu = 0
        self.vm_ram = 0
        self.vm_swap = 0
        self.vm_image = image
        self.vm_nic = ''
        self.os_options = ''
        self.raw_data = ''
        self.nic_ip = 'ip_public = "$NIC[IP, NETWORK=\\"public\\"]",\n'
        self.extra_context = ''
        self.one_home = ''
        self.user_key_path = options.userKey
        self.user_key_name = os.path.basename(options.userKey)

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

    @staticmethod
    def getVmTemplatesParameters():
        params = (
            'vm_cpu',
            'vm_ram',
            'vm_swap',
            'vm_image',
            'vm_nic',
            'os_options',
            'raw_data',
            'nic_ip',
            'extra_context',
            'one_home',
            'user_key_path',
            'user_key_name'
        )
        return params

    def _buildVmTemplate(self, template):
        baseVmTemplate = fileGetContent(template)
        self.vm_cpu, self.vm_ram, self.vm_swap = self.getInstanceType().get(self.instanceType)

        self._manageOsOptions()
        self._manageNic()
        self._manageRawData()
        self._manageExtraContext()

        return baseVmTemplate % self._vmParamDict()

    def _vmParamDict(self):
        params = {}
        for param in self.getVmTemplatesParameters():
            params[param] = getattr(self, param, '')

        return params

    def _manageOsOptions(self):
        if not self.vmKernel and not self.vmRamdisk:
            return

        if self.vmKernel:
            self.os_options += 'kernel = "%s"' % self.vmKernel

        if self.vmRamdisk:
            if self.vmKernel:
                self.os_options += ', '
            self.os_options += 'initrd = "%s"' % self.vmRamdisk

        self.os_options = 'OS = [ %s ]' % self.os_options

    def _manageNic(self):
        if validateIp(self.addressing):
            self.vm_nic += 'NIC = [ network = "public", ip = "%s" ]\n' % self.addressing
            self.defaultVmNic.remove('public')

        if self.addressing == 'private':
            self.defaultVmNic.remove('public')
            self.nic_ip = ''

        if self.extraNic:
            self.defaultVmNic.append(self.extraNic)
            self.nic_ip += 'ip_extra = "$NIC[IP, NETWORK=\\"%s\\"]",\n' % self.extraNic

        for nic in self.defaultVmNic:
            self.vm_nic += 'NIC = [ network = "%s" ]\n' % nic

    def _manageRawData(self):
        if self.rawData:
            self.raw_data = 'RAW = [ type="%s", data="%s" ]' % (self.config.get('hypervisor'),
                                                                self.rawData)

    def _manageExtraContext(self):
        extraContext = {}
        contextElems = []

        if self.extraContextFile:
            contextFile = open(self.extraContextFile, 'rb')
            contextFileData = contextFile.read()
            contextFile.close()
            contextElems.extend(contextFileData.split('\n'))

        if self.extraContextData:
            contextElems.extend(self.extraContextData.split(cliLineSplitChar))

        for line in contextElems:
            if len(line) == 0:
                continue

            contextLine = line.split('=')

            if len(contextLine) < 2:
                printError('Error while parsing contextualization file.\n'
                           'Syntax error in line `%s`' % line)

            extraContext[contextLine[0]] = ('%s' % cliLineSplitChar).join(contextLine[1:])

        print extraContext
        contextData = ['%s = %s,' % (key, value) for key, value in extraContext.items()]

        self.extra_context = '\n'.join(contextData)

    def runInstance(self):
        vmTpl = self._buildVmTemplate(self.vmTemplatePath)

        plurial = { True: 'machines',
                    False: 'machine' }

        printAction('Starting %s %s' % (self.instanceNumber,
                                        plurial.get(self.instanceNumber > 1)))

        for vm in range(self.instanceNumber):
            try:
                vmId = self.cloud.vmStart(vmTpl)
            except Exception, e:
                printError(e)
                
            vmIp = self.cloud.getVmIp(vmId).get('public', 'No public IP')
            printStep('VM %s : ID %s, IP %s' % (vm, vmId, vmIp))

        printAction('Done!')
        