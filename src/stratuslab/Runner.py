import os
import re
import sys

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
        self.vncPort = options.vncPort
        self.vncListen = options.vncListen

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(options.username, options.password)

        # NIC which are set by default
        # networkType: { 'name': 'MyNetworkNameInOne', 'ip': 'ForcedIp' }, ...
        # Set ip != 0 to force assignation
        # networkType are public, private and extra (can be other but not used in init.sh)
        self.defaultVmNic = { 'public': {
                                'name': 'public',
                                'ip': 0 },
                              'private': {
                                'name': 'private',
                                'ip': 0 },
                            }

        # VM template parameters initialization
        self.vm_cpu = 0
        self.vm_ram = 0
        self.vm_swap = 0
        self.vm_image = image
        self.vm_nic = ''
        self.os_options = ''
        self.raw_data = ''
        self.nic_ip = ''
        self.nic_netmask = ''
        self.nic_network = ''
        self.extra_context = ''
        self.graphics = ''
        self.one_home = self.config.get('one_home')
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
            'nic_netmask',
            'nic_network',
            'extra_context',
            'graphics',
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
        self._manageVnc()

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
            self.defaultVmNic['public']['ip'] = self.addressing

        if self.addressing == 'private':
            del self.defaultVmNic['public']

        if self.extraNic:
            if self.extraNic not in self.cloud.getNetworkPoolNames():
                printError('Network %s does not exist' % self.extraNic)

            extraNic = {'name': self.extraNic, 'ip': 0}
            self.defaultVmNic['extra'] = extraNic

        for type, nicInfo in self.defaultVmNic.items():
            nicIp = (nicInfo['ip'] != 0) and (', ip = "%s"' % nicInfo['ip']) or ''
            vnetId = self.cloud.networkNameToId(nicInfo['name'])
            self.vm_nic += ('NIC = [ network = "%s" %s ]\n' % (nicInfo['name'], nicIp))
            self.nic_ip += ('\nip_%s = "$NIC[IP, NETWORK=\\"%s\\"]",' % (type, nicInfo['name']))
            self.nic_network += ('\nnetwork_%s = "%s",' % (type, self.cloud.getNetworkAddress(vnetId)))
            self.nic_netmask += ('\nnetmask_%s = "%s",' % (type, self.cloud.getNetworkNetmask(vnetId)))

    def _manageRawData(self):
        if self.rawData:
            if os.path.isfile(self.rawData):
                dataFile = open(self.rawData, 'rb')
                self.rawData = dataFile.read()
                dataFile.close()
            self.rawData = re.escape(self.rawData)
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

        contextData = ['%s = %s,' % (key, value) for key, value in extraContext.items()]

        self.extra_context = '\n'.join(contextData)

    def _manageVnc(self):
        vncInfo = []

        if self.vncPort:
            vncInfo.append('port = "%s"' % self.vncPort)

        if self.vncListen:
            vncInfo.append('listen = "%s"' % self.vncListen)

        if len(vncInfo) > 0:
            vncInfo.append('type = "vnc"')

            self.graphics = 'GRAPHICS = [\n%s\n]' % (',\n'.join(vncInfo))

    def runInstance(self):
        vmTpl = self._buildVmTemplate(self.vmTemplatePath)

        plurial = { True: 'machines',
                    False: 'machine' }

        printAction('Starting %s %s' % (self.instanceNumber,
                                        plurial.get(self.instanceNumber > 1)))

        for vmNb in range(self.instanceNumber):
            try:
                vmId = self.cloud.vmStart(vmTpl)
            except Exception, e:
                printError(e)

            vmIps = ['\t%s IP: %s' % (name, ip)
                        for name, ip in self.cloud.getVmIp(vmId).items()]
            printStep('Machine %s (vm ID: %s)\n%s' % (vmNb+1, vmId, '\n'.join(vmIps)))

        printAction('Done!')
        