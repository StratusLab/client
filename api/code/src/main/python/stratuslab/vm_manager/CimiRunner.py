#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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
import json
import os
import urllib2

import stratuslab.Util as Util
from stratuslab.Util import printStep, printAction
import stratuslab.Exceptions as Exceptions
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Authn import AuthnFactory
from stratuslab.image.Image import Image
from stratuslab import Defaults
from stratuslab.AuthnCommand import CloudEndpoint
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from marketplace.Util import Util as MarketplaceUtil
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.volume_manager.volume_manager import VolumeManager


class CimiRunner(object):
    """
    This class is a drop-in replacement for the standard Runner that
    will start a virtual machine via the StratusLab CIMI interface.
    """

    class HeadRequest(urllib2.Request):
        def get_method(self):
            return "HEAD"

    # FIXME: Need to add in the treatment of create_image

    DISKS_BUS_AVAILABLE = ['ide', 'scsi', 'virtio']
    DISKS_BUS_DEFAULT = ManifestInfo.DISKS_BUS_DEFAULT
    DISKS_BUS_PREFIX_MAP = {'ide': 'hd',
                            'scsi': 'sd',
                            'virtio': 'vd'}
    vmDisksBus = None

    DEFAULT_INSTANCE_TYPE = 'm1.small'

    def __init__(self, image, configHolder):
        if image == '':
            raise ValueError('Image ID should be provided.')

        self.vm_image = image
        self.persistentDiskUUID = None
        self.readonlyDiskId = None
        self.extraDiskSize = None
        self.instanceNumber = 1
        self.authorEmail = ''
        self.marketplaceEndpointNewimage = ''
        self.pdiskEndpoint = None
        self.endpoint = None
        self.instanceType = CimiRunner.DEFAULT_INSTANCE_TYPE
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

        self.createImageData = {}
        self._init_vm_attributes()

        self.instancesDetail = []

        self.availableInstanceTypes = self._get_available_instance_types()

        self._validate_instance_type()

    def _setCloudContext(self):
        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)

        if not self.pdiskEndpoint:
            self.pdiskEndpoint = self.endpoint

        self.endpoint = self.cloud.setEndpoint(self.endpoint)
        self.pdisk = None

    def _get_available_instance_types(self):
        availableTypes = CimiRunner.getDefaultInstanceTypes()
        userDefinedTypes = self.userDefinedInstanceTypes

        availableTypes.update(userDefinedTypes)

        return availableTypes

    def _validate_instance_type(self):
        if self.instanceType not in self.availableInstanceTypes:
            raise ValueError('Unknown instance type: %s' % self.instanceType)

    def _init_vm_attributes(self):
        if not self.vm_image:
            return

        self._initVmAttributesStatic()

        self._set_msg_recipients()
        self._set_user_key_if_defined()
        self._setSaveDisk()
        self._set_disk_image_format()
        self._set_disks_bus_type()

    def _initVmAttributesStatic(self):
        # VM template parameters initialization
        self.vm_cpu = 0
        self.vm_vcpu = 0
        self.vm_ram = 0
        self.vm_swap = 0
        self.vm_nic = ''
        self.vm_name = ''
        self.vm_disks_prefix = CimiRunner.DISKS_BUS_PREFIX_MAP[CimiRunner.DISKS_BUS_DEFAULT]
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

    def _set_msg_recipients(self):
        try:
            self.msgRecipients
        except AttributeError:
            self.msgRecipients = []

    def _set_disk_image_format(self):
        useQcowDiskFormat = getattr(self, 'useQcowDiskFormat', False)
        # if image ID was provided extract disk driver type from manifest
        if self.vm_image:
            if not useQcowDiskFormat and Image.isImageId(self.vm_image):
                image = Image(self.configHolder)
                self.disk_driver = image.getImageFormatByImageId(self.vm_image)
                return
        self.disk_driver = (useQcowDiskFormat and 'qcow2') or 'raw'

    def _set_disks_bus_type(self):
        if self.vmDisksBus:
            disks_bus = self.vmDisksBus
        else:
            if Image.isImageId(self.vm_image):
                image = Image(self.configHolder)
                disks_bus = image.getImageDisksBusTypeByImageId(self.vm_image)
            else:
                return

        try:
            self.vm_disks_prefix = CimiRunner.DISKS_BUS_PREFIX_MAP[disks_bus]
        except KeyError:
            raise Exception('Unknown disks bus type %s' % disks_bus)

    def _set_user_key_if_defined(self):
        if getattr(self, 'userPublicKeyFile', None):
            self.public_key = ''
            for line in file(self.userPublicKeyFile):
                if not line.startswith('Comment:'):
                    self.public_key += line

    def _setSaveDisk(self):
        self.save_disk = self.saveDisk and 'yes' or 'no'

    @staticmethod
    def getDefaultInstanceTypes():
        types = {
            # name      :   (cpu, ram, swap)
            't1.micro': (1, 512, 512),
            'm1.small': (1, 1536, 1536),
            'm1.medium': (1, 3072, 3072),
            'm1.large': (2, 6144, 6144),
            'm1.xlarge': (4, 8192, 8192),
            'c1.medium': (2, 1536, 1536),
            'c1.xlarge': (4, 6144, 6144),
        }
        return types

    @staticmethod
    def getVmTemplatesParameters(instance=None):
        return []

    @staticmethod
    def getTemplatePath(instance=None):
        return None

    @staticmethod
    def defaultRunOptions():

        _sshPublicKey = os.getenv('STRATUSLAB_KEY', Defaults.sshPublicKeyLocation)
        _sshPrivateKey = _sshPublicKey.strip('.pub')
        defaultOp = {'userPublicKeyFile': _sshPublicKey,
                     'userPrivateKeyFile': _sshPrivateKey,
                     'instanceNumber': 1,
                     'instanceType': CimiRunner.DEFAULT_INSTANCE_TYPE,
                     'vmTemplateFile': None,
                     'rawData': '',
                     'vmKernel': '',
                     'vmRamdisk': '',
                     'vmName': '',
                     'vmCpuAmount': None,
                     'vmCpu': None,
                     'vmRam': None,
                     'vmSwap': None,
                     'vmDisksBus': CimiRunner.vmDisksBus,
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

    def _build_machine_template(self):
        """
        Generate the VM template from this instance's parameters.  This
        returns a JSON string representation of the machine template.
        """

        machine_template_data = self._build_machine_template_data()
        return json.dumps(machine_template_data)

    def _build_machine_template_data(self):
        """
        Builds a data structure that mirrors the JSON representation of
        a CIMI MachineTemplate.  The returned data structure can be serialized
        directly to JSON.
        """

        machine_template = {}

        machine_template = self._add_metadata(machine_template)

        machine_template = self._add_machine_configuration(machine_template)

        machine_template = self._add_machine_image(machine_template)

        machine_template = self._add_volumes(machine_template)

        machine_template = self._add_network_interfaces(machine_template)

        # self._manageRawData()
        # self._manageExtraContext()
        # self._manageVnc()
        # self._manageCreateImage()
        # self._manageInboundPorts()

        return machine_template

    def _add_metadata(self, machine_template):
        if self.vmName:
            machine_template['name'] = self.vmName

        return machine_template

    def _add_machine_configuration(self, machine_template):

        machine_config = {}
        machine_config = self._add_cpu_ram_swap(machine_config)

        machine_template['machineConfig'] = machine_config

        return machine_template

    def _add_machine_image(self, machine_template):
        machine_image = {'type': 'IMAGE',
                         'imageLocation': self.vm_image}

        machine_template['machineImage'] = machine_image

        return machine_template

    def _add_volumes(self, machine_template):
        # TODO: References should actually be to CIMI Volume not pdisk/Marketplace URIs.

        volumes = []

        if self.pdiskEndpointHostname and self.pdiskPort and self.persistentDiskUUID:
            ref = 'pdisk:%s:%s:%s' % \
                  (self.pdiskEndpointHostname, str(self.pdiskPort), self.persistentDiskUUID)
            volume = {'volume': {'href': ref}}
            volumes.append(volume)

        if hasattr(self, 'readonlyDiskId') and self.readonlyDiskId:
            self.readonlyDiskId = self._prependMarketplaceUrlIfImageId(self.readonlyDiskId)
            ref = self.readonlyDiskId
            volume = {'volume': {'href': ref}}
            volumes.append(volume)

        machine_template['volumes'] = volumes

        return machine_template

    def _add_network_interfaces(self, machine_template):
        # TODO: Determine how mapping to CIMI really will work.

        interface = {'network': {'href': self._get_network_name()}}

        if self.specificAddressRequest:
            address = {'href': self.specificAddressRequest}
            interface['addresses'] = [address]

        machine_template['networkInterfaces'] = [interface]
        return machine_template

    def _add_cpu_ram_swap(self, machineConfig):
        vm_cpu, vm_ram_mib, vm_swap_mb = self.getInstanceResourceValues()

        vm_ram_kib = 1024 * vm_ram_mib
        vm_swap_kb = 1000 * vm_swap_mb

        swap_disk = {'capacity': vm_swap_kb,
                     'format': 'swap',
                     'initialLocation': '%sb' % self.vm_disks_prefix}

        # TODO: The architecture should be set by the user; not hardcoded.
        machineConfig['cpu'] = vm_cpu
        machineConfig['cpuArch'] = 'x86_64'

        machineConfig['memory'] = vm_ram_kib

        if 'disks' in machineConfig:
            disks = machineConfig['disks']
        else:
            disks = []

        disks.append(swap_disk)

        if self.extraDiskSize:
            size_kb = 1000 * 1000 * self.extraDiskSize
            volatile_disk = {'capacity': size_kb,
                             'format': 'ext4',
                             'initialLocation': '%sc' % self.vm_disks_prefix}
            machineConfig['disks'].append(volatile_disk)

        machineConfig['disks'] = disks

        return machineConfig

    def _get_network_name(self):
        networkName = 'public'
        if self.isLocalIp:
            networkName = 'local'
        elif self.isPrivateIp:
            networkName = 'private'
        return networkName

    def runInstance(self, details=False):
        self._print_contacting()

        if Image.isImageId(self.vm_image):
            self.vm_image = self._prependMarketplaceUrlIfImageId(self.vm_image)
        elif Image.isDiskId(self.vm_image):
            self.vm_image = self._createDiskUrlIfDiskId(self.vm_image)
        elif self._is_alias_url(self.vm_image):
            self.vm_image = self._resolve_url(self.vm_image)
        else:
            raise Exceptions.ValidationException('Image reference must be an '
                                                 'Alias URL, Marketplace Image ID or Disk ID:  %s' %
                                                 self.vm_image)

        printAction('Starting machine(s)')

        vmTpl = self._build_machine_template()

        label = (self.instanceNumber > 1) and 'machines' or 'machine'

        printStep('Starting %s %s' % (self.instanceNumber, label))

        self._print_detail('on endpoint: %s' % self.endpoint, Util.VERBOSE_LEVEL_DETAILED)
        self._print_detail('with template:\n%s' % vmTpl, Util.VERBOSE_LEVEL_DETAILED)

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
        self._print_contacting()
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
        self._operate_on_instance('Kill', ids=ids)

    def shutdownInstances(self, ids=[]):
        self._operate_on_instance('Shutdown', ids=ids)

    def _is_alias_url(self, url):
        # TODO: Put in real implementation.
        return True

    def _operate_on_instance(self, operation, ids=[]):
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
            self._print_detail('Sending "%s" request for instance %s.' % (operation, vmId))
            instance_operation(int(vmId))
        plural = (len(vmIds) > 1 and 's') or ''
        self._print_detail('"%s" %s VM%s: %s' % (operation, len(vmIds), plural,
                                                 ', '.join(map(str, vmIds))))

    def _print_detail(self, msg, verboseLevel=Util.VERBOSE_LEVEL_NORMAL):
        return Util.printDetail(msg, self.verboseLevel, verboseLevel)

    def waitUntilVmRunningOrTimeout(self, vmId, vmStartTimeout=120, failOn=()):
        return self.cloud.waitUntilVmRunningOrTimeout(vmId, vmStartTimeout, failOn=failOn)

    def getVmState(self, vmId):
        return self.cloud.getVmState(vmId)

    def _prependMarketplaceUrlIfImageId(self, image):
        if Image.isImageId(image):
            return MarketplaceUtil.metadataUrl(self.marketplaceEndpoint, image)
        else:
            return image

    def _createDiskUrlIfDiskId(self, image):
        if Image.isDiskId(image):
            self.pdiskEndpointHostname = VolumeManager.getFQNHostname(self.pdiskEndpoint)
            return "pdisk:%s:%s:%s" % (self.pdiskEndpointHostname, self.pdiskPort, image)
        else:
            return image

    def _print_contacting(self):
        self._print_detail('Accessing compute service at: %s' % self.endpoint)

    def _resolve_url(self, url):
        """Uses a HEAD request to resolve an http(s) URL with a possible redirect."""
        if url.startswith("http"):
            response = urllib2.urlopen(CimiRunner.HeadRequest(url))
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
