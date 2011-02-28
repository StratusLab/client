#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import re

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import cliLineSplitChar
from stratuslab.Util import fileGetContent
from stratuslab.Util import modulePath
from stratuslab.Util import printStep
import stratuslab.Util as Util
from stratuslab.Authn import AuthnFactory
from stratuslab.Exceptions import ValidationException

class Runner(object):

    EXTRA_DISK = '''DISK=[
  FORMAT=ext3,
  READONLY=no,
  SAVE=no,
  SIZE=%(extraDiskSize)s,
  TARGET=hdd,
  TYPE=fs ]'''

    def __init__(self, image, configHolder):
        configHolder.assign(self)

        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.cloud.setEndpoint(self.endpoint)

        self.vm_image = image

        self._initAttributes()

    def _initAttributes(self):
        # VM template parameters initialization
        self.vm_cpu = 0
        self.vm_ram = 0
        self.vm_swap = 0
        self.vm_nic = ''
        self.os_options = ''
        self.raw_data = ''
        self.extra_context = ''
        self.graphics = ''
        self.vmIds = []
        self.disk_driver = None

        self._setUserKeyIfDefined()
        self._setSaveDisk()
        self._setExtraDiskOptional()
        self._setDiskImageFormat()

    def _setDiskImageFormat(self):
        useQcowDiskFormat = getattr(self, 'useQcowDiskFormat', False)
        self.disk_driver = (useQcowDiskFormat and 'qcow2') or 'raw'

    def _setUserKeyIfDefined(self):
        if getattr(self, 'userPublicKeyFile', None):
            self.public_key = fileGetContent(self.userPublicKeyFile)

    def _setSaveDisk(self):
        saveDisk = getattr(self, 'saveDisk', False)
        self.save_disk = (saveDisk and 'yes') or 'no'

    def _setExtraDiskOptional(self):
        try:
            self.extra_disk = (self.extraDiskSize and Runner.EXTRA_DISK % self.__dict__) or ''
        except AttributeError:
            pass

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
        vmTemplate = Runner.getTemplatePath(instance)

        fd = open(vmTemplate, 'rb')
        template = fd.read()
        fd.close()

        return [Runner._extractTokenName(token) for token in Runner._findTokensInTemplate(template)]

    @staticmethod
    def getTemplatePath(instance=None):
        vmTemplate = ''
        if instance and hasattr(instance, 'vmTemplatePath'):
            vmTemplate = instance.vmTemplatePath
        if not os.path.exists(vmTemplate):
            vmTemplate = Util.shareDir +'vm/schema.one'
        if not os.path.exists(vmTemplate):
            vmTemplate = '%s/../../../share/vm/schema.one' % modulePath
        return vmTemplate

    @staticmethod
    def _findTokensInTemplate(template):
        return re.findall('%\(\w+\)s', template)

    @staticmethod
    def _extractTokenName(token):
        return re.sub(r'%\((\w+)\)s', r'\1', token)

    @staticmethod
    def defaultRunOptions():
        return {'userPublicKeyFile': os.getenv('STRATUSLAB_KEY', ''),
                'userPrivateKeyFile': os.getenv('STRATUSLAB_KEY', '').strip('.pub'),
                'endpoint': os.getenv('STRATUSLAB_ENDPOINT', ''),
                'instanceNumber': 1,
                'instanceType': 'm1.small',
                'vmTemplatePath': Runner.getTemplatePath(),
                'rawData': '',
                'vmKernel': '',
                'vmRamdisk': '',
                'isLocalIp': False,
                'isPrivateIp': False,
                'extraContextFile': '',
                'extraContextData': '',
                'vncPort': None,
                'vncListen': '',
                'specificAddressRequest': None,
                'diskFormat': 'raw',
                'saveDisk': 'no',
                'inVmIdsFile': None,
                'outVmIdsFile': None }

    def _buildVmTemplate(self, template):
        baseVmTemplate = fileGetContent(template)
        self.vm_cpu, self.vm_ram, self.vm_swap = self.getInstanceType().get(self.instanceType)

        self._manageOsOptions()
        self._manageNetwork()
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


    def _manageNetwork(self):
        networkName = self._getNetworkName()
        networkPrefix = 'NIC = [ network = "%s" ' % networkName
        networkPostfix = ']\n'
        if self.specificAddressRequest:
            self.vm_nic = networkPrefix + ',\nIP = "%s"' % self.specificAddressRequest + networkPostfix
        else:
            self.vm_nic = networkPrefix + networkPostfix

    def _getNetworkName(self):
        networkName = 'public'
        if self.isLocalIp:
            networkName = 'local'
        elif self.isPrivateIp:
            networkName = 'private'
        return networkName

    def _manageRawData(self):
        if self.rawData:
            if os.path.isfile(self.rawData):
                dataFile = open(self.rawData, 'rb')
                self.rawData = dataFile.read()
                dataFile.close()
            self.rawData = re.escape(self.rawData)
            hypervisor = 'kvm'
            self.raw_data = 'RAW = [ type="%s", data="%s" ]' % (hypervisor,
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
                Util.printError('Error while parsing contextualization file.\n'
                                'Syntax error in line `%s`' % line)

            extraContext[contextLine[0]] = '='.join(contextLine[1:])

        contextData = ['%s = "%s",' % (key, value) for key, value in extraContext.items()]

        self._appendContextData(contextData)

    def _appendContextData(self, context):
        self.extra_context += '\n'.join(context)

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
        self._checkImageUrl()

        vmTpl = self._buildVmTemplate(self.vmTemplatePath)

        plurial = { True: 'machines',
                    False: 'machine' }

        printStep('Starting %s %s' % (self.instanceNumber,
                                        plurial.get(self.instanceNumber > 1)))

        self.printDetail('on endpoint: %s' % self.endpoint)
        self.printDetail('with template:\n%s' % vmTpl)

        for vmNb in range(self.instanceNumber):
            vmId = self.cloud.vmStart(vmTpl)
            self.vmIds.append(vmId)
            networkName, ip = self.getNetworkDetail(vmId)
            vmIpPretty = '\t%s ip: %s' % (networkName.title(), ip)
            printStep('Machine %s (vm ID: %s)\n%s' % (vmNb+1, vmId, vmIpPretty))

        self._saveVmIds()

        return self.vmIds

    def getNetworkDetail(self, vmId):
        networkName, ip = self.cloud.getVmIp(vmId)
        return networkName, ip

    def _saveVmIds(self):
        if self.outVmIdsFile:
            open(self.outVmIdsFile,'w').write('\n'.join(map(str,self.vmIds)))

    def _loadVmIdsFromFile(self):
        vmIds = []

        if self.inVmIdsFile:
            vmIds = open(self.inVmIdsFile).read().split('\n')

        return vmIds

    def killInstances(self, ids):
        _ids = ids
        if self.inVmIdsFile:
            _ids = self._loadVmIdsFromFile()
        for id in _ids:
            self.cloud.vmKill(int(id))
        plural = (len(_ids) > 1 and 's') or ''
        self.printDetail('Killed %s VM%s: %s' % (len(_ids), plural, ', '.join(map(str,_ids))))

    def printDetail(self, msg):
        return Util.printDetail(msg, self.verboseLevel, Util.DETAILED_VERBOSE_LEVEL)

    def waitUntilVmRunningOrTimeout(self, vmId, vmStartTimeout=120):
        vmStarted = self.cloud.waitUntilVmRunningOrTimeout(vmId, vmStartTimeout)
        return vmStarted

    def _checkImageUrl(self):
        return
        self.printDetail('Checking image availability.')
        if self.noCheckImageUrl:
            Util.printWarning('Image availability check was disabled.')
            return
        extentionToMime = {'gz' :'application/x-gzip',
                           'bz2':'application/x-bzip'}
        mimeType = Util.guessMimeTypeByExtension(self.vm_image)
        if not Util.pingFile(self.image, mimeType):
            raise ValidationException('Unable to access the base image: %s' % self.image)
#        try:
#            Util.checkUrlExists(self.vm_image, timeout=5)
#        except ExecutionException, e:
#            Util.printError('Image availability check: %s' % str(e))
        self.printDetail('Image available: %s' % self.vm_image)
