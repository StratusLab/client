#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
import urllib2

import stratuslab.Util as Util
from stratuslab.Util import printStep, printAction, printWarning, printError
import stratuslab.Exceptions as Exceptions
import stratuslab.cloudinit.Util as CloudInitUtil
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Authn import AuthnFactory
from stratuslab.image.Image import Image
from stratuslab import Defaults
from stratuslab.AuthnCommand import CloudEndpoint
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from stratuslab.vm_manager.vm_manager import VmManager
from stratuslab.volume_manager.volume_manager import VolumeManager
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.marketplace.Util import Util as MarketplaceUtil


class Runner(VmManager):
    class HeadRequest(urllib2.Request):
        def get_method(self):
            return "HEAD"

    EXTRA_DISK = '''DISK=[
  FORMAT=ext3,
  READONLY=no,
  SAVE=no,
  SIZE=%(extraDiskSize)s,
  TARGET=%(vm_disks_prefix)sc,
  TYPE=fs ]'''

    # Don't hard code disk target to allow multiple pdisk attachment
    # NOTE: The pdiskEndpoint must NOT have a trailing slash.
    PERSISTENT_DISK = '''DISK=[
  SOURCE=pdisk:%(pdiskEndpoint)s/%(persistentDiskUUID)s,
  TARGET=%(vm_disks_prefix)sc,
  TYPE=block ]'''

    # NOTE: The READONLY flag must NOT be set to true.  This will result
    # in a deployment.0 file that libvirt cannot deploy.  The device type
    # must also be kept with 'disk' and NOT 'cdrom', otherwise the
    # contextualization will not work correctly.  GitHub Issue #50.
    READONLY_DISK = '''DISK=[
  SOURCE="%(readonlyDiskId)s",
  READONLY=no,
  SAVE=no,
  TARGET=%(vm_disks_prefix)sc,
  DRIVER="raw" ]'''

    CREATE_IMAGE = '''CREATE_IMAGE = [
%s
]'''

    def __init__(self, image, configHolder):
        super(Runner, self).__init__(image, configHolder)

        self.vm_image = image
        self.persistentDiskUUID = None
        self.readonlyDiskId = None
        self.extraDiskSize = None
        self.instanceNumber = 1
        self.authorEmail = ''
        self.marketplaceEndpointNewimage = ''
        self.pdiskEndpoint = None
        self.endpoint = None
        self.instanceType = Runner.DEFAULT_INSTANCE_TYPE
        self.vmCpu = ''
        self.vmRam = ''
        self.vmSwap = ''
        self.vmCpuAmount = ''
        self.vmName = ''
        self.vmKernel = ''
        self.vmRamdisk = ''
        self.isLocalIp = False
        self.isPrivateIp = False
        self.specificAddressRequest = False
        self.rawData = ''
        self.extraContextFile = ''
        self.extraContextData = ''
        self.cloudInit = ''
        self.vncPort = ''
        self.vncListen = ''
        self.noCheckImageUrl = False
        self.saveDisk = False
        self.userDefinedInstanceTypes = {}
        self.pdiskPort = Defaults.pdiskPort
        self.inboundPorts = None
        configHolder.assign(self)
        self.configHolder = configHolder
        self._setCloudContext()
        self.createImageData = {self.CREATE_IMAGE_KEY_CREATOR_EMAIL: self.authorEmail,
                                self.CREATE_IMAGE_KEY_NEWIMAGE_MARKETPLACE: self.marketplaceEndpointNewimage}
        self._initVmAttributes()
        self.instancesDetail = []
        self.availableInstanceTypes = self._getAvailableInstanceTypes()
        self._validateInstanceType()

    def _setCloudContext(self):
        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)

        if not self.pdiskEndpoint:
            self.pdiskEndpoint = self.endpoint

        self.endpoint = self.cloud.setEndpoint(self.endpoint)
        self.pdisk = None

    def _getAvailableInstanceTypes(self):
        availableTypes = Runner.getDefaultInstanceTypes()
        userDefinedTypes = self.userDefinedInstanceTypes

        availableTypes.update(userDefinedTypes)

        return availableTypes

    def _validateInstanceType(self):
        if self.instanceType not in self.availableInstanceTypes:
            raise ValueError('Unknown instance type: %s' % self.instanceType)

    def _initVmAttributes(self):
        if not self.vm_image:
            return

        self._initVmAttributesStatic()

        self._setMsgRecipients()
        self._setUserKeyIfDefined()
        self._setSaveDisk()
        self._setDiskImageFormat()
        self._setDisksBusType()
        self._setInboundPorts()

        # should go after all runtime fields are initialized
        self._setExtraDiskOptional()
        self._setPersistentDiskOptional()
        self._setReadonlyDiskOptional()

    def _initVmAttributesStatic(self):
        # VM template parameters initialization
        self.vm_cpu = 0
        self.vm_vcpu = 0
        self.vm_ram = 0
        self.vm_swap = 0
        self.vm_nic = ''
        self.vm_name = ''
        self.vm_disks_prefix = Runner.DISKS_BUS_PREFIX_MAP[Runner.DISKS_BUS_DEFAULT]
        self.vm_requirements = ''
        self.os_options = ''
        self.raw_data = ''
        self.extra_context = ''
        self.graphics = ''
        self.vmIds = []
        self.vmIdsAndNetwork = []
        self.diskImageFormat = None
        self.disk_driver = None
        self.inbound_ports = ''

    def _setMsgRecipients(self):
        try:
            self.msgRecipients
        except AttributeError:
            self.msgRecipients = []

    def _setDiskImageFormat(self):
        useQcowDiskFormat = getattr(self, 'useQcowDiskFormat', False)
        # if image ID was provided extract disk driver type from manifest
        if self.vm_image:
            if not useQcowDiskFormat and Image.isImageId(self.vm_image):
                image = Image(self.configHolder)
                self.disk_driver = image.getImageFormatByImageId(self.vm_image)
                return
        self.disk_driver = (useQcowDiskFormat and 'qcow2') or 'raw'

    def _setDisksBusType(self):
        if self.vmDisksBus:
            disks_bus = self.vmDisksBus
        else:
            if Image.isImageId(self.vm_image):
                image = Image(self.configHolder)
                disks_bus = image.getImageDisksBusTypeByImageId(self.vm_image)
            else:
                return

        try:
            self.vm_disks_prefix = Runner.DISKS_BUS_PREFIX_MAP[disks_bus]
        except KeyError:
            raise Exception('Unknown disks bus type %s' % disks_bus)

    def _setUserKeyIfDefined(self):
        if getattr(self, 'userPublicKeyFile', None):
            self.public_key = ''
            for line in file(self.userPublicKeyFile):
                if not line.startswith('Comment:'):
                    self.public_key += line

    def _setSaveDisk(self):
        self.save_disk = self.saveDisk and 'yes' or 'no'

    def _setExtraDiskOptional(self):
        try:
            self.extra_disk = (self.extraDiskSize and Runner.EXTRA_DISK % self.__dict__) or ''
        except AttributeError:
            pass

    def _setPersistentDiskOptional(self):
        if not self.persistentDiskUUID:
            return

        self.pdiskEndpointHostname = VolumeManager.getFQNHostname(self.pdiskEndpoint)

        # Ensure that the pdiskEndpoint does not have a trailing slash.
        opts = self.__dict__.copy()
        opts['pdiskEndpoint'] = self.pdiskEndpoint.rstrip('/')

        self.persistent_disk = (self.persistentDiskUUID and Runner.PERSISTENT_DISK % opts) or ''

        self._checkPersistentDiskAvailable()

    def _checkPersistentDiskAvailable(self):
        self.pdisk = VolumeManagerFactory.create(self.configHolder)
        try:
            available, _ = self.pdisk.getVolumeUsers(self.persistentDiskUUID)
            if self.instanceNumber > available:
                printError(
                    'disk cannot be attached; it is already mounted (%s/%s)' % (available, self.instanceNumber))
        except AttributeError:
            printError('Persistent disk service unavailable', exit=False)
            raise
        except Exception as e:
            printError(e, exit=False)
            raise

    def _setReadonlyDiskOptional(self):
        if hasattr(self, 'readonlyDiskId') and self.readonlyDiskId:
            self._checkImageExists(self.readonlyDiskId)
            self.readonlyDiskId = self._prependMarketplaceUrlIfImageId(self.readonlyDiskId)
            self.readonly_disk = (self.readonlyDiskId and Runner.READONLY_DISK % self.__dict__) or ''

    def _setInboundPorts(self):
        if Image.isImageId(self.vm_image):
            image = Image(self.configHolder)
            try:
                self.inboundPorts = image.getInboundPortsByImageId(self.vm_image)
            except Exceptions.ExecutionException:
                pass

    @staticmethod
    def getVmTemplatesParameters(instance=None):
        vmTemplate = Runner.getTemplatePath(instance)

        fd = open(vmTemplate, 'rb')
        template = fd.read()
        fd.close()

        return [Runner._extractTokenName(token) for token in Runner._findTokensInTemplate(template)]

    @staticmethod
    def getTemplatePath(instance=None):
        if instance and hasattr(instance, 'vmTemplateFile'):
            return Util.get_share_file(['vm', 'schema.one'], instance.vmTemplateFile)
        else:
            return Util.get_share_file(['vm', 'schema.one'])

    @staticmethod
    def _findTokensInTemplate(template):
        return re.findall('%\(\w+\)s', template)

    @staticmethod
    def _extractTokenName(token):
        return re.sub(r'%\((\w+)\)s', r'\1', token)

    @staticmethod
    def defaultRunOptions():

        _sshPublicKey = os.getenv('STRATUSLAB_KEY', Defaults.sshPublicKeyLocation)
        _sshPrivateKey = _sshPublicKey.strip('.pub')
        defaultOp = {'userPublicKeyFile': _sshPublicKey,
                     'userPrivateKeyFile': _sshPrivateKey,
                     'instanceNumber': 1,
                     'instanceType': Runner.DEFAULT_INSTANCE_TYPE,
                     'vmTemplateFile': Runner.getTemplatePath(),
                     'rawData': '',
                     'vmKernel': '',
                     'vmRamdisk': '',
                     'vmName': '',
                     'vmCpuAmount': None,
                     'vmCpu': None,
                     'vmRam': None,
                     'vmSwap': None,
                     'vmDisksBus': Runner.vmDisksBus,
                     'vmRequirements': '',
                     'isLocalIp': False,
                     'isPrivateIp': False,
                     'extraContextFile': '',
                     'extraContextData': '',
                     'cloudInit': '',
                     # FIXME: hack to fix a weird problem with network in CentOS on Fedora 14 + KVM.
                     #        Network is not starting unless VNC is defined. Weird yeh...? 8-/
                     'vncPort': '-1',
                     #'vncPort': None,

                     'vncListen': '',
                     'specificAddressRequest': None,
                     'diskFormat': 'raw',
                     'saveDisk': False,
                     'inVmIdsFile': None,
                     'outVmIdsFile': None,
                     'noCheckImageUrl': False,
                     'msgRecipients': [],
                     'marketplaceEndpoint': Defaults.marketplaceEndpoint,
                     'authorEmail': ''}
        defaultOp.update(CloudEndpoint.options())
        defaultOp.update(PDiskEndpoint.options())
        return defaultOp

    def getInstanceResourceValues(self):

        try:
            cpu, ram, swap = self.availableInstanceTypes.get(self.instanceType)
        except AttributeError:
            cpu, ram, swap = self.getDefaultInstanceTypes().get(self.instanceType)
        if self.vmCpu is not None:
            cpu = self.vmCpu
        if self.vmRam is not None:
            ram = self.vmRam
        if self.vmSwap is not None:
            swap = self.vmSwap

        return cpu, ram, swap

    def _buildVmTemplate(self, template):
        baseVmTemplate = Util.fileGetContent(template)

        self._manageCpuRamSwap()
        self._manageVmName()
        self._manageOsOptions()
        self._manageNetwork()
        self._manageRawData()
        self._manageExtraContext()
        self._manageVnc()
        self._manageCreateImage()
        self._manageRequirements()
        self._manageInboundPorts()

        return baseVmTemplate % self._vmParamDict()

    def _vmParamDict(self):
        params = {}
        for param in self.getVmTemplatesParameters(self):
            params[param] = getattr(self, param, '')

        return params

    def _manageInboundPorts(self):
        if self.inboundPorts:
            self.inbound_ports = 'INBOUND_PORTS = "%s"' % ','.join(self.inboundPorts)
        else:
            self.inbound_ports = ''

    def _manageCpuRamSwap(self):
        self.vm_cpu, self.vm_ram, self.vm_swap = self.getInstanceResourceValues()
        self.vm_vcpu = self.vm_cpu
        if self.vmCpuAmount and self.vmCpuAmount <= self.vm_cpu:
            self.vm_cpu = self.vmCpuAmount

    def _manageVmName(self):
        if self.vmName:
            self.vm_name = 'NAME = "%s"' % self.vmName
        else:
            self.vm_name = ''

    def _manageRequirements(self):
        if self.vmRequirements:
            self.vm_requirements = 'REQUIREMENTS = "%s"' % self.vmRequirements
        else:
            self.vm_requirements = ''

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
        networkPrefix = 'NIC = [ network_uname=oneadmin,network = "%s" ' % networkName
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
            contextElems.extend(self.extraContextData.split(Util.cliLineSplitChar))

        if self.cloudInit:
            cloudInitArgs = self.cloudInit.split(Util.cliLineSplitChar)
            cloudInitData = CloudInitUtil.contextFile(cloudInitArgs)
            contextElems.extend(cloudInitData.split('\n'))

        for line in contextElems:
            if len(line) == 0:
                continue

            contextLine = line.split('=')

            if len(contextLine) < 2:
                printError('Error while parsing contextualization file.\n'
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

    def _manageCreateImage(self):
        if not self.saveDisk:
            return

        data = ['%s = "%s"' % (k, v) for k, v in self.createImageData.items()]
        self.create_image = Runner.CREATE_IMAGE % ',\n'.join(data)

    def updateCreateImageTemplateData(self, updateDict):
        self.createImageData.update(updateDict)

    def runInstance(self, details=False):
        self._printContacting()

        if Image.isImageId(self.vm_image):
            self._checkImageExists(self.vm_image)
            self.vm_image = self._prependMarketplaceUrlIfImageId(self.vm_image)
        elif Image.isDiskId(self.vm_image):
            self.vm_image = self._createDiskUrlIfDiskId(self.vm_image)
        elif self._isAliasUrl(self.vm_image):
            self.vm_image = self._resolveUrl(self.vm_image)
        else:
            raise Exceptions.ValidationException('Image reference must be an '
                                                 'Alias URL, Marketplace Image ID or Disk ID:  %s' %
                                                 self.vm_image)

        printAction('Starting machine(s)')

        self.printDetail('Using VM template file: %s' % self.vmTemplateFile)

        vmTpl = self._buildVmTemplate(self.vmTemplateFile)

        label = (self.instanceNumber > 1) and 'machines' or 'machine'

        printStep('Starting %s %s' % (self.instanceNumber, label))

        self.printDetail('on endpoint: %s' % self.endpoint, Util.VERBOSE_LEVEL_DETAILED)
        self.printDetail('with template:\n%s' % vmTpl, Util.VERBOSE_LEVEL_DETAILED)

        for vmNb in range(self.instanceNumber):
            vmId = self.cloud.vmStart(vmTpl)
            self.vmIds.append(vmId)
            networkName, ip = self.getNetworkDetail(vmId)
            self.vmIdsAndNetwork.append((vmId, networkName, ip))
            vmIpPretty = '\t%s ip: %s' % (networkName.title(), ip)
            printStep('Machine %s (vm ID: %s)\n%s' % (vmNb + 1, vmId, vmIpPretty))
            self.instancesDetail.append({'id': vmId, 'ip': ip, 'networkName': networkName})
        self._saveVmIds()

        printStep('Done!')

        if not details:
            return self.vmIds
        else:
            return self.vmIdsAndNetwork

    def save_instance_as_new_image(self, vm_id):
        self._printContacting()
        self._checkInstanceExists(vm_id)

        printStep('Instructing cloud to save instance as new image on shutdown')

    def getNetworkDetail(self, vmId):
        networkName, ip = self.cloud.getVmIp(vmId)
        return networkName, ip

    def _saveVmIds(self):
        if self.outVmIdsFile:
            open(self.outVmIdsFile, 'w').write('\n'.join(map(str, self.vmIds)))

    def _loadVmIdsFromFile(self):
        vmIds = []

        if self.inVmIdsFile:
            vmIds = open(self.inVmIdsFile).read().split('\n')

        return vmIds

    def killInstances(self, ids=[]):
        self._operateOnInstance('Kill', ids=ids)

    def shutdownInstances(self, ids=[]):
        self._operateOnInstance('Shutdown', ids=ids)

    def _isAliasUrl(self, url):
        # TODO: Put in real implementation.
        return True

    def _operateOnInstance(self, operation, ids=[]):
        operations = ('Shutdown', 'Kill')
        if operation not in operations:
            raise Exceptions.ExecutionException('Unsupported operation on instance: %s' %
                                                operation)
        vmIds = ids or self.vmIds
        if self.inVmIdsFile:
            vmIds = self._loadVmIdsFromFile()
        if operation == 'Shutdown':
            instance_operation = self.cloud.vmStop
        if operation == 'Kill':
            instance_operation = self.cloud.vmKill
        for vmId in vmIds:
            self.printDetail('Sending "%s" request for instance %s.' % (operation, vmId))
            instance_operation(int(vmId))
        plural = (len(vmIds) > 1 and 's') or ''
        self.printDetail('"%s" %s VM%s: %s' % (operation, len(vmIds), plural,
                                               ', '.join(map(str, vmIds))))

    def printDetail(self, msg, verboseLevel=Util.VERBOSE_LEVEL_NORMAL):
        return Util.printDetail(msg, self.verboseLevel, verboseLevel)

    def waitUntilVmRunningOrTimeout(self, vmId, vmStartTimeout=120, failOn=()):
        return self.cloud.waitUntilVmRunningOrTimeout(vmId, vmStartTimeout, failOn=failOn)

    def getVmState(self, vmId):
        return self.cloud.getVmState(vmId)

    def _checkImageExists(self, imageId):
        self.printDetail('Checking image availability.')
        if self.noCheckImageUrl:
            printWarning('Image availability check is disabled.')
            return
        imageObject = Image(self.configHolder)
        imageObject.checkImageExists(imageId)

    def _prependMarketplaceUrlIfImageId(self, image):
        if Image.isImageId(image):
            return MarketplaceUtil.metadataUrl(self.marketplaceEndpoint, image)
        else:
            return image

    def _createDiskUrlIfDiskId(self, image):
        if Image.isDiskId(image):
            self.pdiskEndpointHostname = VolumeManager.getFQNHostname(self.pdiskEndpoint)
            return "pdisk:%s/%s" % (self.pdiskEndpoint.rstrip('/'), image)
        else:
            return image

    def _printContacting(self):
        self.printDetail('Accessing compute service at: %s' % self.endpoint)

    def _resolveUrl(self, url):
        """Uses a HEAD request to resolve an http(s) URL with a possible redirect."""
        if url.startswith("http"):
            response = urllib2.urlopen(Runner.HeadRequest(url))
            return response.geturl()
        else:
            return url

    def listInstanceTypes(self):
        types = self.availableInstanceTypes

        columnSize = 10

        output = ''
        output += ' '.ljust(1)
        output += 'Type'.ljust(columnSize)
        output += 'CPU'.rjust(columnSize)
        output += 'RAM'.rjust(columnSize)
        output += 'SWAP'.rjust(columnSize)
        output += "\n"
        for name in sorted(types.iterkeys()):
            flag = (name == self.instanceType and '*') or ' '
            cpu, ram, swap = types[name]
            output += "%s %s %s %s %s\n" % (flag.ljust(1),
                                            name.ljust(columnSize),
                                            ('%s CPU' % cpu).rjust(columnSize),
                                            ('%s MB' % ram).rjust(columnSize),
                                            ('%s MB' % swap).rjust(columnSize))

        return output
