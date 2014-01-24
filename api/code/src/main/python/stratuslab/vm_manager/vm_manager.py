#!/usr/bin/env python
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

import os

from stratuslab.ManifestInfo import ManifestInfo
from stratuslab import Defaults
from stratuslab.AuthnCommand import CloudEndpoint
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
import stratuslab.Util as Util


class VmManager(object):
    """
    Provides an abstract interface for different VM manager
    implementations.  The initial interface is exactly the same
    public interface presented by the old Runner class.
    """

    CREATE_IMAGE_KEY_CREATOR_EMAIL = 'CREATOR_EMAIL'
    CREATE_IMAGE_KEY_CREATOR_NAME = 'CREATOR_NAME'
    CREATE_IMAGE_KEY_NEWIMAGE_TITLE = 'NEWIMAGE_TITLE'
    CREATE_IMAGE_KEY_NEWIMAGE_COMMENT = 'NEWIMAGE_COMMENT'
    CREATE_IMAGE_KEY_NEWIMAGE_VERSION = 'NEWIMAGE_VERSION'
    CREATE_IMAGE_KEY_NEWIMAGE_MARKETPLACE = 'NEWIMAGE_MARKETPLACE'
    CREATE_IMAGE_KEY_MSG_TYPE = 'MSG_TYPE'
    CREATE_IMAGE_KEY_MSG_ENDPOINT = 'MSG_ENDPOINT'
    CREATE_IMAGE_KEY_MSG_QUEUE = 'MSG_QUEUE'
    CREATE_IMAGE_KEY_MSG_MESSAGE = 'MSG_MESSAGE'

    DEFAULT_INSTANCE_TYPE = 'm1.small'
    vmDisksBus = None
    DISKS_BUS_AVAILABLE = ['ide', 'scsi', 'virtio']
    DISKS_BUS_DEFAULT = ManifestInfo.DISKS_BUS_DEFAULT
    DISKS_BUS_PREFIX_MAP = {'ide': 'hd',
                            'scsi': 'sd',
                            'virtio': 'vd'}

    def __init__(self, image=None, config_holder=None):
        if image == '':
            raise ValueError('Image ID must be provided.')

        if config_holder is None:
            config_holder = ConfigHolder()

        self.vm_image = image
        self.configHolder = config_holder


    @staticmethod
    def getTemplatePath(instance=None):
        if instance and hasattr(instance, 'vmTemplateFile'):
            return Util.get_share_file(['vm', 'schema.one'], instance.vmTemplateFile)
        else:
            return Util.get_share_file(['vm', 'schema.one'])


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
    def defaultRunOptions():
        raise NotImplementedError()

    @staticmethod
    def defaultRunOptions():

        _sshPublicKey = os.getenv('STRATUSLAB_KEY', Defaults.sshPublicKeyLocation)
        _sshPrivateKey = _sshPublicKey.strip('.pub')
        default_options = {'userPublicKeyFile': _sshPublicKey,
                           'userPrivateKeyFile': _sshPrivateKey,
                           'instanceNumber': 1,
                           'instanceType': VmManager.DEFAULT_INSTANCE_TYPE,
                           'vmTemplateFile': VmManager.getTemplatePath(),
                           'rawData': '',
                           'vmKernel': '',
                           'vmRamdisk': '',
                           'vmName': '',
                           'vmCpuAmount': None,
                           'vmCpu': None,
                           'vmRam': None,
                           'vmSwap': None,
                           'vmDisksBus': VmManager.vmDisksBus,
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
        default_options.update(CloudEndpoint.options())
        default_options.update(PDiskEndpoint.options())
        return default_options

    def getInstanceResourceValues(self):
        raise NotImplementedError()

    def updateCreateImageTemplateData(self, updateDict):
        raise NotImplementedError()

    def runInstance(self, details=False):
        raise NotImplementedError()

    def save_instance_as_new_image(self, vm_id):
        raise NotImplementedError()

    def getNetworkDetail(self, vmId):
        raise NotImplementedError()

    def killInstances(self, ids=None):
        raise NotImplementedError()

    def shutdownInstances(self, ids=None):
        raise NotImplementedError()

    def printDetail(self, msg, verboseLevel=Util.VERBOSE_LEVEL_NORMAL):
        raise NotImplementedError()

    def waitUntilVmRunningOrTimeout(self, vmId, vmStartTimeout=120, failOn=()):
        raise NotImplementedError()

    def getVmState(self, vmId):
        raise NotImplementedError()

    def listInstanceTypes(self):
        raise NotImplementedError()
