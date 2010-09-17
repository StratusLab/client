import os
import re

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import assignAttributes
from stratuslab.Util import cliLineSplitChar
from stratuslab.Util import fileGetContent
from stratuslab.Util import modulePath
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import validateIp
from stratuslab.Util import randomString

class Runner(object):

    def __init__(self, image, options):
        assignAttributes(self, options)

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setEndpoint(self.endpoint)
        
        self.cloud.setCredentials(self.username, self.password)

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
        self.nicOrder = ['private', 'public', 'extra']

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
        self.extra_context = ''
        self.graphics = ''
        self.public_key = fileGetContent(self.userKey)
        self.vmIps = None
        self.save_disk = self.saveDisk and 'yes' or 'no'
        self.vmIds = []

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
    def getVmTemplatesParameters(instance=None):
        if instance and hasattr(instance, 'vmTemplatePath'):
            vmTemplate = instance.vmTemplatePath
        else:
            vmTemplate = Runner.defaultRunOptions().get('vmTemplatePath')

        fd = open(vmTemplate, 'rb')
        template = fd.read()
        fd.close()

        return [Runner._extractTokenName(token) for token in Runner._findTokensInTemplate(template)]

    @staticmethod
    def _findTokensInTemplate(template):
        return re.findall('%\(\w+\)s', template)

    @staticmethod
    def _extractTokenName(token):
        return re.sub(r'%\((\w+)\)s', r'\1', token)

    @staticmethod        
    def defaultRunOptions():
        options = {'configFile': '%s/conf/stratuslab.cfg' % modulePath,
                   'userKey': os.getenv('STRATUSLAB_KEY', ''),
                   'username': os.getenv('STRATUSLAB_USERNAME', ''),
                   'password': os.getenv('STRATUSLAB_PASSWORD', ''),
                   'endpoint': os.getenv('STRATUSLAB_ENDPOINT', ''),
                   'instanceNumber': 1,
                   'instanceType': 'm1.small',
                   'vmTemplatePath': '%s/share/vm/schema.one' % modulePath,
                   'extraNic': '',
                   'rawData': '',
                   'vmKernel': '',
                   'vmRamdisk': '',
                   'addressing': '',
                   'extraContextFile': '',
                   'extraContextData': '',
                   'vncPort': None,
                   'vncListen': '',
                   'saveDisk': 'no' }
        return options

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
        for param in self.getVmTemplatesParameters(self):
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

            extraNic = {'name': self.extraNic, 'ip': 0 }
            self.defaultVmNic['extra'] = extraNic

        for nicName in self.nicOrder:
            if nicName not in self.defaultVmNic:
                return
            nicInfo = self.defaultVmNic.get(nicName)
            nicIp = (nicInfo['ip'] != 0) and (', ip = "%s"' % nicInfo['ip']) or ''
            vnetId = self.cloud.networkNameToId(nicInfo['name'])
            
            self.vm_nic += ('NIC = [ network = "%s"%s ]\n' % (nicInfo['name'], nicIp))
            self.nic_ip += ('\nip_%s = "$NIC[IP, NETWORK=\\"%s\\"]",' % (nicName, nicInfo['name']))

            netmask = self.cloud.getNetworkNetmask(vnetId)
            if netmask:
                self.nic_netmask += ('\nnetmask_%s = "/%s",' % (nicName, netmask))

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

            extraContext[contextLine[0]] = '='.join(contextLine[1:])

        contextData = ['%s = "%s",' % (key, value) for key, value in extraContext.items()]

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

    def _addRunnerContext(self):
        context = [
            'stratuslab_internal_key=%s' % randomString()
        ]

        self.extraContextData.extend(context)

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
            self.vmIds.append(vmId)
            self.vmIps = self.cloud.getVmIp(vmId).items()
            vmIpsPretty = ['\t%s IP: %s' % (name, ip) for name, ip in self.vmIps]
            printStep('Machine %s (vm ID: %s)\n%s' % (vmNb+1, vmId, '\n'.join(vmIpsPretty)))

        printAction('Done!')
        return self.vmIds

    def waitUntilVmRunningOrTimeout(self, vmId):
        vmStarted = self.cloud.waitUntilVmRunningOrTimeout(vmId, 120)
        return vmStarted

    def stopInstance(self, vmId):
        vmStopped = self.cloud.vmStop(vmId)
        return vmStopped
