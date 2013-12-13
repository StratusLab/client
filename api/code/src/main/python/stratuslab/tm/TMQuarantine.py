#!/usr/bin/env python
#
# Copyright (c) 2013, SixSq Sarl
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
import shutil
import re
from os.path import dirname
from getpass import getuser

from stratuslab.Util import defaultConfigFile, sshCmdWithOutput
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.Defaults import sshPublicKeyLocation
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from stratuslab.Util import is_uuid


class TMQuarantine(object):
    """Quarantine the files for a terminated virtual machine"""

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSE_LEVEL = 0

    # Position of the provided args
    _ARG_SRC_POS = 1

    _PDISK_PORT = 8445

    def __init__(self, args, **kwargs):
        self.args = args

        self.diskSrcPath = None
        self.diskSrcHost = None
        self.vmDir = None
        self.diskName = None
        self.pdiskHostPort = None
        self.snapshotMarketplaceId = None
        self.targetMarketplace = None
        self.createdPDiskId = None
        self.p12cert = ''
        self.p12pswd = None
        self.pdiskEndpoint = None
        self.pdiskPath = None
        self.pdiskPathNew = None
        self.originImageIdUrl = None
        self.originImageId = None
        self.originMarketPlace = None
        self.instanceId = None
        self.cloud = None

        self.rootVolumeUuid = None

        self.persistentDiskIp = None
        self.persistentDiskLvmDevice = None

        self._initFromConfig(kwargs.get('conf_filename', ''))

        self._initCloudConnector()

    def run(self):
        try:
            self._run()
        finally:
            self._cleanup()

    def _run(self):
        self._checkArgs()
        self._parseArgs()
        self._retrieveInstanceId()
        self._retrieveVmDir()
        self._retrieveAttachedVolumeInfo()
        self._detachAllVolumes()
        self._changeOwnerOfSnapshotVolume()
        self._moveFilesToQuarantine()

    def _initFromConfig(self, conf_filename=''):
        config = ConfigHolder.configFileToDictWithFormattedKeys(conf_filename or
                                                                defaultConfigFile)
        options = PDiskEndpoint.options()
        self.configHolder = ConfigHolder(options, config)
        self.configHolder.set('pdiskEndpoint', self.configHolder.persistentDiskIp)
        self.configHolder.set('verboseLevel', self.DEFAULT_VERBOSE_LEVEL)
        self.configHolder.assign(self)

    def _initCloudConnector(self):
        credentials = LocalhostCredentialsConnector(self.configHolder)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.cloud.setEndpointFromParts('localhost', self.configHolder.onePort)

    def _checkArgs(self):
        if len(self.args) != 2:
            raise ValueError('Invalid number of arguments')

    def _parseArgs(self):
        src = self.args[self._ARG_SRC_POS]
        self.diskSrcPath = self._getDiskPath(src)
        self.diskSrcHost = self._getDiskHost(src)

    def _changeOwnerOfSnapshotVolume(self):
        pdisk = VolumeManagerFactory.create(self.configHolder)

        # root volume may not exist, if this is an image creation
        # only actually change ownership of snapshot volumes
        if self.rootVolumeUuid:
            disk_identifier = pdisk.getValue('identifier', self.rootVolumeUuid)
            if re.match('.*snapshot.*', disk_identifier):
                pdisk.quarantineVolume(self.rootVolumeUuid)

    def _moveFilesToQuarantine(self):
        instance_dir = os.path.join(self.vmDir, str(self.instanceId))
        quarantine_dir = os.path.join(self.vmDir, 'quarantine')
        self._moveFilesToQuarantineLocal(instance_dir, quarantine_dir)
        self._moveFilesToQuarantineHypervisor(instance_dir, quarantine_dir)

    def _moveFilesToQuarantineLocal(self, instance_dir, quarantine_dir):
        shutil.move(instance_dir, quarantine_dir)

    def _moveFilesToQuarantineHypervisor(self, instance_dir, quarantine_dir):
        self._sshDst(['mv', instance_dir, quarantine_dir],
                     'Failed to quarantine VM on hypervisor.')

    #--------------------------------------------
    # Persistent disk and related
    #--------------------------------------------

    def _retrieveAttachedVolumeInfo(self):
        uris = self._getAttachedVolumeURIs()
        self.attachedVolumeURIs = uris

    def _getAttachedVolumeURIs(self):
        register_filename_contents = self._sshDst(['/usr/sbin/stratus-list-registered-volumes.py',
                                                   '--vm-id', str(self.instanceId)],
                                                  'Unable to get registered volumes')
        return self._sanitizeVolumeURIs(register_filename_contents.splitlines())

    def _sanitizeVolumeURIs(self, volume_uris):
        "Filtering assumes that the disk's name is UUID."
        return filter(lambda x: is_uuid(self._getDiskNameFromURI(x.strip())),
                      volume_uris)

    def _getDiskNameFromURI(self, uri):
        return uri.split(':')[-1]

    def _getPDiskHostPortFromURI(self, uri):
        splittedUri = uri.split(':')
        self._assertLength(splittedUri, 4)
        return ':'.join(splittedUri[1:3])

    def _detachAllVolumes(self):
        pdisk = VolumeManagerFactory.create(self.configHolder)

        msg = ''
        self.rootVolumeUuid = None
        for pdisk_uri in self.attachedVolumeURIs:

            pdisk_uri = pdisk_uri.strip()

            if pdisk_uri:
                # saves the root volume uuid so that the ownership can be changed later
                if not self.rootVolumeUuid:
                    self.rootVolumeUuid = self._getDiskNameFromURI(pdisk_uri)

                try:
                    self._detachSingleVolume(pdisk, pdisk_uri)
                except Exception as e:
                    msg += str(e) + "\n"

        if msg:
            raise Exception(msg)

    def _detachSingleVolume(self, pdisk, pdisk_uri):
        uuid = self._getDiskNameFromURI(pdisk_uri)
        turl = pdisk.getTurl(uuid)
        self._sshDst(['/usr/sbin/stratus-pdisk-client.py',
                      '--pdisk-id', pdisk_uri,
                      '--vm-id', str(self.instanceId),
                      '--turl', turl,
                      '--register', '--mark', '--attach', '--op', 'down'],
                     'Unable to detach pdisk "%s with TURL %s on VM %s"' %
                     (pdisk_uri, turl, str(self.instanceId)))

    #--------------------------------------------
    # Utility
    #--------------------------------------------

    def _assertLength(self, elem, size):
        if len(elem) != size:
            raise ValueError('List should have %s element(s), got %s' % (size, len(elem)))

    def _getDiskPath(self, arg):
        return self._getStringPart(arg, 1)

    def _getDiskHost(self, arg):
        return self._getStringPart(arg, 0)

    def _findNumbers(self, elems):
        findedNb = []
        for nb in elems:
            try:
                findedNb.append(int(nb))
            except Exception:
                pass
        return findedNb

    def _getStringPart(self, arg, part, nbPart=2, delimiter=':'):
        path = arg.split(delimiter)
        self._assertLength(path, nbPart)
        return path[part]

    def _retrieveInstanceId(self):
        pathElems = self.diskSrcPath.split('/')
        instanceId = self._findNumbers(pathElems)
        errorMsg = '%s instance ID in path. ' + 'Path is "%s"' % self.diskSrcPath
        if len(instanceId) != 1:
            raise ValueError(errorMsg % ((len(instanceId) == 0) and 'Unable to find'
                                         or 'Too many candidates'))
        self.instanceId = instanceId.pop()

    def _retrieveVmDir(self):
        self.vmDir = dirname(dirname(self.diskSrcPath))

    def _sshDst(self, cmd, errorMsg, dontRaiseOnError=False):
        return self._ssh(self.diskSrcHost, cmd, errorMsg, dontRaiseOnError)

    def _ssh(self, host, cmd, errorMsg, dontRaiseOnError=False):
        retCode, output = sshCmdWithOutput(' '.join(cmd), host, user=getuser(),
                                           sshKey=sshPublicKeyLocation.replace('.pub', ''))
        if not dontRaiseOnError and retCode != 0:
            raise Exception('%s\n: Error: %s' % (errorMsg, output))
        return output

    def _cleanup(self):
        pass
