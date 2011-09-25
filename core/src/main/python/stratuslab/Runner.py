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

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
import stratuslab.Util as Util
from stratuslab.Authn import AuthnFactory
from stratuslab.Image import Image
from stratuslab import Defaults
from stratuslab.AuthnCommand import CloudEndpoint, PDiskEndpoint
from stratuslab.PersistentDisk import PersistentDisk
from marketplace.Util import Util as MarketplaceUtil

class Runner(object):

    EXTRA_DISK = '''DISK=[
  FORMAT=ext3,
  READONLY=no,
  SAVE=no,
  SIZE=%(extraDiskSize)s,
  TARGET=hdc,
  TYPE=fs ]'''

    # Don't hard code disk target to allow multiple pdisk attachment
    PERSISTENT_DISK = '''DISK=[
  SOURCE=pdisk:%(pdiskEndpointHostname)s:%(pdiskPort)s:%(persistentDiskUUID)s,
  TARGET=hdc,
  TYPE=block ]'''

    READONLY_DISK = '''DISK=[
  SOURCE="%(readonlyDiskId)s",
  READONLY=yes,
  SAVE=no,
  TARGET=hdc,
  DRIVER="raw" ]'''

    NOTIFICATION = '''NOTIFICATION = [
  HOST="{0}",
  VHOST="{1}",
  USER="{2}",
  PASSWORD="{3}",
  QUEUE="{4}" ]'''

    defaultInstanceType = 'm1.small'

    def __init__(self, image, configHolder):
        if image == '':
            raise ValueError('Image ID or full image endpoint should be provided.')
        self.vm_image = image
        self.persistentDiskUUID = None
        self.quiet = False
        self.instanceNumber = 1
        configHolder.assign(self)
        self.configHolder = configHolder

        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.cloud.setEndpoint(self.endpoint)
        self.pdisk = PersistentDisk(configHolder)


        self._initAttributes()
        
        self.instancesDetail = []

    def _initAttributes(self):
        # VM template parameters initialization
        self.vm_cpu = 0
        self.vm_vcpu = 0
        self.vm_ram = 0
        self.vm_swap = 0
        self.vm_nic = ''
        self.vm_name = ''
        self.os_options = ''
        self.raw_data = ''
        self.extra_context = ''
        self.graphics = ''
        self.vmIds = []
        self.diskImageFormat = None
        self.disk_driver = None
        self.msgRecipients = []

        self._setUserKeyIfDefined()
        self._setSaveDisk()
        self._setExtraDiskOptional()
        self._setPersistentDiskOptional()
        self._setReadonlyDiskOptional()
        self._setDiskImageFormat()

    def _setDiskImageFormat(self):
        useQcowDiskFormat = getattr(self, 'useQcowDiskFormat', False)
        # if image ID was provided extract disk driver type from manifest
        if self.vm_image:
            if not useQcowDiskFormat and Image.isImageId(self.vm_image):
                image = Image(self.configHolder)
                self.disk_driver = image.getImageFormatByImageId(self.vm_image)
                return
        self.disk_driver = (useQcowDiskFormat and 'qcow2') or 'raw'

    def _setUserKeyIfDefined(self):
        if getattr(self, 'userPublicKeyFile', None):
            self.public_key = ''
            for line in file(self.userPublicKeyFile):
                if not line.startswith('Comment:'):
                    self.public_key += line

    def _setSaveDisk(self):
        saveDisk = getattr(self, 'saveDisk', False)
        self.save_disk = (saveDisk and 'yes') or 'no'

    def _setExtraDiskOptional(self):
        try:
            self.extra_disk = (self.extraDiskSize and Runner.EXTRA_DISK % self.__dict__) or ''
        except AttributeError:
            pass

    def _setPersistentDiskOptional(self):
        try:
            if not self.persistentDiskUUID:
                return
            self.pdiskEndpointHostname = PersistentDisk.getFQNHostname(self.pdiskEndpoint)
            self.persistent_disk = (self.persistentDiskUUID and Runner.PERSISTENT_DISK % self.__dict__) or ''
            available, _ = self.pdisk.getVolumeUsers(self.persistentDiskUUID)
            if self.instanceNumber > available:
                Util.printError('Only %s/%s disk(s) can be attached. Aborting' 
                                % (available, self.instanceNumber))
        except AttributeError:
            Util.printError('Persistent disk service unavailable')
        except Exception, e:
            Util.printError(e)

    def _setReadonlyDiskOptional(self):
        if hasattr(self, 'readonlyDiskId') and self.readonlyDiskId:
            self._checkImageExists(self.readonlyDiskId)
            self.readonlyDiskId = self._prependMarketplaceUrlIfImageId(self.readonlyDiskId)
            self.readonly_disk = (self.readonlyDiskId and Runner.READONLY_DISK % self.__dict__) or ''

    @staticmethod
    def getInstanceType():
        types = {
            # name      :   (cpu, ram, swap)
            't1.micro'  :   (1, 128, 512),
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
        if instance and hasattr(instance, 'vmTemplateFile'):
            vmTemplate = instance.vmTemplateFile
        if not os.path.exists(vmTemplate):
            vmTemplate = os.path.join(Defaults.SHARE_DIR +'vm/schema.one')
        if not os.path.exists(vmTemplate):
            vmTemplate = '%s/../../../share/vm/schema.one' % Util.modulePath
        return vmTemplate

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
                    'instanceType': Runner.defaultInstanceType,
                    'vmTemplateFile': Runner.getTemplatePath(),
                    'rawData': '',
                    'vmKernel': '',
                    'vmRamdisk': '',
                    'vmName': '',
                    'vmCpuAmount': None,
                    'isLocalIp': False,
                    'isPrivateIp': False,
                    'extraContextFile': '',
                    'extraContextData': '',
                    # FIXME: hack to fix a weird problem with network in CentOS on Fedora 14 + KVM. 
                    #        Network is not starting unless VNC is defined. Weird yeh...? 8-/
                    'vncPort': '-1',
                    #'vncPort': None,
                    
                    'vncListen': '',
                    'specificAddressRequest': None,
                    'diskFormat': 'raw',
                    'saveDisk': 'no',
                    'inVmIdsFile': None,
                    'outVmIdsFile': None,
                    'noCheckImageUrl': False,
                    'msgRecipients' : [],
                    'marketplaceEndpoint' : Defaults.marketplaceEndpoint }
        defaultOp.update(CloudEndpoint.options())
        defaultOp.update(PDiskEndpoint.options())
        return defaultOp

    def _buildVmTemplate(self, template):
        baseVmTemplate = Util.fileGetContent(template)
        self.vm_cpu, self.vm_ram, self.vm_swap = self.getInstanceType().get(self.instanceType)
        self.vm_vcpu = self.vm_cpu

        if self.vmCpuAmount and self.vmCpuAmount <= self.vm_cpu:
            self.vm_cpu = self.vmCpuAmount

        if self.vmName:
            self.vm_name = 'NAME = "%s"' % self.vmName
        else:
            self.vm_name = ''

        self._manageOsOptions()
        self._manageNetwork()
        self._manageRawData()
        self._manageExtraContext()
        self._manageVnc()
        self._manageNotifications()

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
            contextElems.extend(self.extraContextData.split(Util.cliLineSplitChar))

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

    def _formatRecipient(self, recipient):
        # fields are: 'host', 'vhost', 'user', 'pass', 'queue'
        # badly formatted inputs are silently ignored
        values = recipient.split(',')
        return Runner.NOTIFICATION.format(*values) if (len(values)==5) else ''

    def _manageNotifications(self):
        if self.msgRecipients:
            notificationInfo = map(self._formatRecipient, self.msgRecipients)
            self.notifications = ('\n'.join(notificationInfo))
        else:
            self.notifications = ''

    def runInstance(self):
        self._checkImageExists(self.vm_image)
        self.vm_image = self._prependMarketplaceUrlIfImageId(self.vm_image)

        self.printAction('Starting machine(s)')

        self.printDetail('Using VM template file: %s' % self.vmTemplateFile)

        vmTpl = self._buildVmTemplate(self.vmTemplateFile)

        plurial = { True: 'machines',
                    False: 'machine' }

        self.printStep('Starting %s %s' % (self.instanceNumber,
                                        plurial.get(self.instanceNumber > 1)))

        self.printDetail('on endpoint: %s' % self.endpoint)
        self.printDetail('with template:\n%s' % vmTpl)

        for vmNb in range(self.instanceNumber):
            vmId = self.cloud.vmStart(vmTpl)
            self.vmIds.append(vmId)
            networkName, ip = self.getNetworkDetail(vmId)
            vmIpPretty = '\t%s ip: %s' % (networkName.title(), ip)
            if self.quiet:
                print '%s, %s' % (vmId, ip)
            else:
                self.printStep('Machine %s (vm ID: %s)\n%s' % (vmNb+1, vmId, vmIpPretty))
            self.instancesDetail.append({'id': vmId, 'ip': ip, 'networkName': networkName})
        self._saveVmIds()

        self.printStep('Done!')

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

    def killInstances(self, ids=[]):
        _ids = ids or self.vmIds
        if self.inVmIdsFile:
            _ids = self._loadVmIdsFromFile()
        for id in _ids:
            self.cloud.vmKill(int(id))
        plural = (len(_ids) > 1 and 's') or ''
        self.printDetail('Killed %s VM%s: %s' % (len(_ids), plural, ', '.join(map(str,_ids))))

    def printDetail(self, msg):
        if self.quiet:
            return
        return Util.printDetail(msg, self.verboseLevel, Util.DETAILED_VERBOSE_LEVEL)

    def printStep(self, msg):
        if self.quiet:
            return
        return Util.printStep(msg)

    def printAction(self, msg):
        if self.quiet:
            return
        return Util.printAction(msg)

    def waitUntilVmRunningOrTimeout(self, vmId, vmStartTimeout=120):
        vmStarted = self.cloud.waitUntilVmRunningOrTimeout(vmId, vmStartTimeout)
        return vmStarted

    def _checkImageExists(self, image):
        '''image - URL or image ID'''
        self.printDetail('Checking image availability.')
        if self.noCheckImageUrl:
            Util.printWarning('Image availability check is disabled.')
            return
        imageObject = Image(self.configHolder)
        imageObject.checkImageExists(image)

    def _prependMarketplaceUrlIfImageId(self, image):
        if Image.re_imageId.match(image):
            return MarketplaceUtil.metadataUrl(self.marketplaceEndpoint, image)
        else:
            return image
