#!/usr/bin/env python
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, SixSq Sarl
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
import re
from time import time
from os.path import dirname
from os.path import basename
from getpass import getuser
from urlparse import urlparse, urlunparse

from stratuslab.Util import sshCmdWithOutput, defaultConfigFile, printStep
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.Defaults import sshPublicKeyLocation
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.marketplace.Policy import Policy
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.Compressor import Compressor
from stratuslab import Util


class TMCloneCache(object):
    """Clone or retrieve from cache disk image"""

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSE_LEVEL = 0

    _ARGS_LEN = 3

    # Position of the provided args
    _ARG_SRC_POS = 1
    _ARG_DST_POS = 2

    _PDISK_PORT = 8445

    _CHECKSUM = 'sha1'

    _ACCEPTED_EXTRA_DISK_TYPE = ['DATA_IMAGE_RAW_READONLY', 'DATA_IMAGE_RAW_READ_WRITE']
    _ACCEPTED_ROOT_DISK_TYPE = 'MACHINE_IMAGE_LIVE'

    _IDENTIFIER_KEY = 'identifier'
    _COUNT_KEY = 'count'
    _TYPE_KEY = 'type'
    _OWNER_KEY = 'owner'
    _VISIBILITY_KEY = 'visibility'

    _PDISK_SUPERUSER = 'pdisk'
    _DISK_UNAUTHORIZED_VISIBILITIES = ['PRIVATE']

    def __init__(self, args, **kwargs):

        self.diskSrc = None
        self.diskDstPath = None
        self.diskDstHost = None
        self.marketplaceEndpoint = None
        self.marketplaceImageId = None
        self.pdiskImageId = None
        self.pdiskSnapshotId = None
        self.downloadedLocalImageLocation = None
        self.downloadedLocalImageSize = 0
        self.vmOwner = None

        self._parseArgs(args)

        self._initFromConfig(kwargs.get('conf_filename', ''))

        self._initPdiskClient()
        self._initMarketplaceRelated()

        self.defaultSignalHandler = None

    def _initFromConfig(self, conf_filename=''):
        config = ConfigHolder.configFileToDictWithFormattedKeys(conf_filename or
                                                                defaultConfigFile)
        options = PDiskEndpoint.options()
        self.configHolder = ConfigHolder(options, config)
        self.configHolder.set('pdiskEndpoint', self._createPdiskEndpoint())
        self.configHolder.set('verboseLevel', self.DEFAULT_VERBOSE_LEVEL)
        self.configHolder.assign(self)

    def _initPdiskClient(self):
        self.pdiskEndpoint = self._createPdiskEndpoint()
        self.pdiskLVMDevice = self.configHolder.persistentDiskLvmDevice
        self.configHolder.set('pdiskEndpoint', self.pdiskEndpoint)
        self.pdisk = VolumeManagerFactory.create(self.configHolder)

    def _initMarketplaceRelated(self):
        self._retrieveMarketplaceInfos()
        self._initManifestDownloader()

    def _initManifestDownloader(self):
        self.manifestDownloader = ManifestDownloader(self.configHolder)

    def run(self):
        self._retrieveDisk()

    def _checkArgs(self, args):
        if len(args) != self._ARGS_LEN:
            raise ValueError('Invalid number of arguments')

    def _parseArgs(self, args):
        self._checkArgs(args)

        dst = args[self._ARG_DST_POS]
        self.diskDstHost = self._getDiskHost(dst)
        self.diskDstPath = self._getDiskPath(dst)
        self.diskSrc = args[self._ARG_SRC_POS]

    # FIXME: duplicates should be pulled into common location
    def _createPdiskEndpoint(self):
        host = self.configHolder.persistentDiskIp
        port = self.configHolder.persistentDiskPort or _PDISK_PORT
        path = self.configHolder.persistentDiskPath or ''
        path = path.strip('/')
        return 'https://%s:%s/%s' % (host, port, path)

    def _updatePDiskSrcUrlFromPublicToLocalIp(self):
        """When PDisk is running behind a proxy, KVMs usually can't connect to
        it on the public IP. Instead substitute the public IP with the local one.
        Substitution is only made if the pdisk URL points to the public IP of the
        PDisk (i.e., the source disk is located on this site).
        persistent_disk_public_base_url should be set in the configuration."""
        src_pdisk_hostname = Util.getHostnameFromUri(self.diskSrc)
        public_pdisk_hostname = Util.getHostnameFromUri(self.persistentDiskPublicBaseUrl) or self.persistentDiskIp
        if src_pdisk_hostname == public_pdisk_hostname:
            disk_src_parts = urlparse(self.diskSrc)
            (scheme, _, path, params, query, fragment) = disk_src_parts
            netloc = self.persistentDiskIp
            if disk_src_parts.port:
                netloc = netloc + ":" + str(disk_src_parts.port)
            self.diskSrc = urlunparse((scheme, netloc, path, params, query, fragment))

    def _retrieveDisk(self):
        if self.diskSrc.startswith('pdisk:'):
            self.diskSrc = self.diskSrc[len('pdisk:'):]  # strip prefix
            self._updatePDiskSrcUrlFromPublicToLocalIp()
            self._startFromPersisted()
        else:
            self._startFromCowSnapshot()

    def _startFromPersisted(self):
        diskId = self.diskSrc.rstrip('/').split('/').pop()
        diskType = self.pdisk.getValue('type', diskId)

        is_root_disk = self._getDiskIndex(self.diskDstPath) is 0
        if is_root_disk:
            self._checkBootDisk(diskId, diskType)
        elif diskType not in self._ACCEPTED_EXTRA_DISK_TYPE:
            raise ValueError('Only %s type disks can be attached as extra disks'
                             % ', '.join(self._ACCEPTED_EXTRA_DISK_TYPE))

        self._createDestinationDir()
        self._attachPDisk(self.diskSrc)
        self._incrementVolumeUserCount(diskId)

    def _incrementVolumeUserCount(self, diskId):
        user_count = self.pdisk.getVolumeUserCount(diskId)
        self.pdisk.updateVolume({self._COUNT_KEY: str(user_count + 1)}, diskId)

    def _checkBootDisk(self, diskId, diskType):
        is_live_machine_disk = diskType in self._ACCEPTED_ROOT_DISK_TYPE
        user_count = self.pdisk.getVolumeUserCount(diskId)

        if not is_live_machine_disk:
            raise Exception('Only a live persistent disk can be booted from.')
        if user_count != 0:
            raise Exception('User count must be zero on the live disk to boot from.')

    def _startFromCowSnapshot(self):
        if self._cacheMiss():
            #self._retrieveAndCachePDiskImage()
            self._remotelyCachePDiskImage()

        try:
            self._checkAuthorization()
            self._createPDiskSnapshot()
            self._setSnapshotOwner()
            self._createDestinationDir()
            self._attachPDisk(self._getPDiskSnapshotURL())
        except:
            self._deletePDiskSnapshot()
            raise

    # -------------------------------------------
    # Cache management and related
    # -------------------------------------------

    def _cacheMiss(self):
        foundIds = self._getPDiskImageIdsFromMarketplaceImageId()
        if len(foundIds) > 0:
            self.pdiskImageId = foundIds[0]
            return False
        return True

    def _createDestinationDir(self):
        dstDir = dirname(self.diskDstPath)
        self._sshDst(['mkdir', '-p', dstDir],
                     'Unable to create directory %s' % dstDir)

    def _downloadImage(self):
        imageLocations = self.manifestDownloader.getImageLocations()
        self._assertLength(imageLocations, 1, atLeast=True)
        imageMarketplaceLocation = imageLocations[0]
        imageName = self._getImageIdFromURI(imageMarketplaceLocation)
        pdiskTmpStore = self._getPDiskTempStore()
        self.downloadedLocalImageLocation = '%s/%s.%s' % (pdiskTmpStore,
                                                          int(time()),
                                                          imageName)
        self._sshPDisk(['curl', '-H', 'accept:application/x-gzip', '-L', '-o',
                        self.downloadedLocalImageLocation, imageMarketplaceLocation],
                       'Unable to download "%s"' % imageMarketplaceLocation)

    def _checkDownloadedImageChecksum(self):
        hash_fun = self._CHECKSUM
        size_b, checksum = self._getDownloadedImageChecksum(hash_fun)
        self._validateImageSize(size_b)
        self._validateImageChecksum(checksum, hash_fun)

    def _getDownloadedImageChecksum(self, hash_fun):
        size_b, sums = Compressor.checksum_file(self.downloadedLocalImageLocation,
                                                [hash_fun])
        return size_b, sums[self._CHECKSUM]

    def _validateImageSize(self, size_b):
        image_size_b = self._getImageSize()
        # convert both to strings to avoid inequality because of type mismatch
        if str(size_b) != str(image_size_b):
            raise ValueError("Downloaded image size (%s) doesn't match size in image manifest (%s)" %
                             (size_b, image_size_b))

    def _validateImageChecksum(self, checksum, hash_fun):
        image_checksum = self._getImageChecksum(hash_fun)
        if checksum != image_checksum:
            raise ValueError('Invalid image checksum: got %s, defined %s' %
                             (checksum, image_checksum))

    def _getImageFormat(self):
        return self.manifestDownloader.getImageElementValue('format')

    def _getImageKind(self):
        return self.manifestDownloader.getImageElementValue('kind')

    def _getImageSize(self):
        return self.manifestDownloader.getImageElementValue('bytes')

    def _getImageChecksum(self, checksum):
        return self.manifestDownloader.getImageElementValue(checksum)

    def _deleteDownloadedImage(self):
        self._sshPDisk(['rm', '-f', self.downloadedLocalImageLocation],
                       'Unable to remove temporary image', True)

    # -------------------------------------------
    # Marketplace and related
    # -------------------------------------------

    def _retrieveMarketplaceInfos(self):
        # Marketplace URLs can start with either http OR https!
        if self.diskSrc.startswith(('http://', 'https://')):
            self.marketplaceEndpoint = self._getMarketplaceEndpointFromURI(self.diskSrc)
            self.marketplaceImageId = self._getImageIdFromURI(self.diskSrc)
        elif self.diskSrc.startswith('pdisk:'):  # Ignore Marketplace if pdisk is used
            self.marketplaceEndpoint = None
            self.marketplaceImageId = None
        else:  # Local marketplace
            self.marketplaceEndpoint = 'http://localhost'
            try:
                self.marketplaceEndpoint = self.configHolder.marketplaceEndpointLocal
            except:
                pass
                # SunStone adds '<hostname>:' to the image ID
            self.marketplaceImageId = self.diskSrc.rstrip('/').split('/').pop()

        if self.marketplaceEndpoint:
            self.configHolder.set('marketplaceEndpoint', self.marketplaceEndpoint)

    def _getMarketplaceEndpointFromURI(self, uri):
        matcher = re.match("^(.*)/metadata/.*$", uri)
        return matcher.group(1)

    def _getImageIdFromURI(self, uri):
        fragments = uri.rstrip('/').split('/')
        return fragments.pop()

    def _validateMarketplaceImagePolicy(self):
        try:
            policy = Policy(self.configHolder)
            policy.check(self.marketplaceImageId)
        except:
            raise Exception('Policy validation failed')

    def _buildFullyQualifiedMarketplaceImage(self, policyCheckResult, imagePos):
        selectedImage = policyCheckResult[imagePos]
        uri = '%s/metadata/%s/%s/%s' % (self.marketplaceEndpoint,
                                        selectedImage.identifier,
                                        selectedImage.endorser,
                                        selectedImage.created)
        return uri

    def _getPDiskImageIdsFromMarketplaceImageId(self):
        return self.pdisk.search(self._IDENTIFIER_KEY, self.marketplaceImageId)

    # -------------------------------------------
    # Persistent disk and related
    # -------------------------------------------

    def _attachPDisk(self, diskSrc):
        uuid = diskSrc.rstrip('/').split('/').pop()
        turl = self.pdisk.getTurl(uuid)
        disk_name = basename(self.diskDstPath)
        vm_id = self._retrieveInstanceId()
        vm_dir = dirname(dirname(dirname(self.diskDstPath)))

        self._sshDst(['/usr/sbin/stratus-pdisk-client.py',
                      '--pdisk-id', diskSrc,
                      '--vm-dir', vm_dir,
                      '--vm-id', str(vm_id),
                      '--vm-disk-name', disk_name,
                      '--turl', turl,
                      '--register', '--mark', '--attach', '--link', '--op', 'up'],
                     'Unable to attach persistent disk: %s, %s, %s, %s, %s' %
                     (diskSrc, vm_dir, str(vm_id), disk_name, turl))

    def _retrieveAndCachePDiskImage(self):
        self.manifestDownloader.downloadManifestByImageId(self.marketplaceImageId)
        self._validateMarketplaceImagePolicy()
        try:
            self._downloadImage()
            self._checkDownloadedImageChecksum()
            self._uploadDownloadedImageToPdisk()
        except:
            self._deletePDiskSnapshot()
            raise
        finally:
            try:
                self._deleteDownloadedImage()
            except:
                pass

    def _remotelyCachePDiskImage(self):
        """
        This function initializes a new persistent volume from a URL.  The image
        contents are downloaded directly from the URL by the persistent disk
        service.  The size (in bytes) and SHA-1 checksum are also validated.
        """

        self.manifestDownloader.downloadManifestByImageId(self.marketplaceImageId)
        self._validateMarketplaceImagePolicy()

        imageLocations = self.manifestDownloader.getImageLocations()
        self._assertLength(imageLocations, 1, atLeast=True)
        url = imageLocations[0]

        sizeInBytes = self._getImageSize()
        sha1 = self._getImageChecksum(self._CHECKSUM)

        gbBytes = 10 ** 9
        sizeInGB = long(sizeInBytes) / gbBytes
        if long(sizeInBytes) % gbBytes > 0:
            sizeInGB += 1

        self.pdiskImageId = self.pdisk.createVolumeFromUrl(sizeInGB, '', False,
                                                           url, str(sizeInBytes), sha1)

        self._setNewPDiskImageOriginProperties()

    def _uploadDownloadedImageToPdisk(self):
        volume_url = self.pdisk.uploadVolume(self.downloadedLocalImageLocation)
        self.pdiskImageId = volume_url.rsplit('/', 1)[1]
        self._setNewPDiskImageOriginProperties()

    def _setNewPDiskImageOriginProperties(self):
        self._setPDiskInfo(self._IDENTIFIER_KEY, self.marketplaceImageId, self.pdiskImageId)
        self._setPDiskInfo(self._TYPE_KEY, 'MACHINE_IMAGE_ORIGIN', self.pdiskImageId)

    def _getPDiskTempStore(self):
        store = self.configHolder.persistentDiskTempStore or '/tmp'
        self._sshDst(['mkdir', '-p', store], 'Unable to create temporary store')
        return store

    def _createPDiskSnapshot(self):
        snapshotIdentifier = 'snapshot:%s' % self.pdiskImageId
        self.pdiskSnapshotId = self.pdisk.createCowVolume(self.pdiskImageId, None)
        self._setPDiskIdentifier(snapshotIdentifier, self.pdiskSnapshotId)

    def _checkAuthorization(self):
        self.vmOwner = self._deriveVMOwner()
        disk_owner = self._getDiskOwner(self.pdiskImageId)
        disk_visibility = self._getDiskVisibility(self.pdiskImageId)
        if disk_owner not in [self.vmOwner, self._PDISK_SUPERUSER] and \
             disk_visibility in self._DISK_UNAUTHORIZED_VISIBILITIES:
            raise ValueError('User %s is not authorized to start image %s' % \
                             (self.vmOwner, self.marketplaceImageId))

    def _setSnapshotOwner(self):
        if not self.vmOwner:
            raise ValueError('VM owner is not set.')
        self.pdisk.updateVolume({'owner': self.vmOwner}, self.pdiskSnapshotId)

    def _setPDiskInfo(self, key, value, pdiskId):
        self.pdisk.updateVolume({key: value}, pdiskId)

    def _setPDiskIdentifier(self, value, pdiskId):
        self.pdisk.updateVolume({self._IDENTIFIER_KEY: value}, pdiskId)

    def _getPDiskSnapshotURL(self):
        return '%s/%s' % (self.pdiskEndpoint, self.pdiskSnapshotId)

    def _deletePDiskSnapshot(self, *args, **kwargs):
        if self.pdiskSnapshotId is None:
            return
        try:
            #FIXME: why do we need to set credentials here?
            self.pdisk._setPDiskUserCredentials()
            self.pdisk.deleteVolume(self.pdiskSnapshotId)
        except:
            pass

    # -------------------------------------------
    # Utility
    # -------------------------------------------

    def _removeExtension(self, filename):
        return '.'.join(filename.split('.')[:-1])

    def _getVirtualSizeBytesFromQemu(self, qemuOutput):
        for line in qemuOutput.split('\n'):
            if line.lstrip().startswith('virtual'):
                bytesAndOtherThings = line.split('(')
                self._assertLength(bytesAndOtherThings)
                bytesAndUnit = bytesAndOtherThings[1].split(' ')
                self._assertLength(bytesAndUnit)
                return int(bytesAndUnit[0])
        raise ValueError('Unable to find image bytes size')

    def _getDiskPath(self, arg):
        return self._getStringPart(arg, 1)

    def _getDiskHost(self, arg):
        return self._getStringPart(arg, 0)

    def _getStringPart(self, arg, part, nbPart=2, delimiter=':'):
        path = arg.split(delimiter)
        self._assertLength(path, nbPart)
        return path[part]

    def _findNumbers(self, elems):
        findedNb = []
        for nb in elems:
            try:
                findedNb.append(int(nb))
            except Exception:
                pass
        return findedNb

    def _getDiskIndex(self, diskPath):
        try:
            return int(diskPath.split('.')[-1])
        except:
            raise ValueError('Unable to determine disk index')

    def _assertLength(self, elements, length=2, errorMsg=None, atLeast=False):
        nbElem = len(elements)
        if not errorMsg:
            errorMsg = 'Object should have a length of %s%s , got %s\n%s' % (length,
                                                                         atLeast and ' at least' or '',
                                                                         nbElem, str(elements))
        if not atLeast and nbElem != length or nbElem < length:
            raise ValueError(errorMsg)

    def _bytesToGiga(self, bytesAmount):
        return (bytesAmount / 1024 ** 3) + 1

    def _sshDst(self, cmd, errorMsg, dontRaiseOnError=False):
        retCode, output = sshCmdWithOutput(' '.join(cmd), self.diskDstHost, user=getuser(),
                                           sshKey=sshPublicKeyLocation.replace('.pub', ''))
        if not dontRaiseOnError and retCode != 0:
            raise Exception('%s\n: Error: %s' % (errorMsg, output))
        return output

    def _sshPDisk(self, cmd, errorMsg, dontRaiseOnError=False):
        cmd_str = ' '.join(cmd)
        printStep("Executing: %s" % cmd_str)
        retCode, output = sshCmdWithOutput(cmd_str, self.pdisk.persistentDiskIp, user=getuser(),
                                           sshKey=self.pdisk.persistentDiskPrivateKey.replace('.pub', ''))
        if not dontRaiseOnError and retCode != 0:
            raise Exception('%s\n: Error: %s' % (errorMsg, output))
        return output

    def _getVMOwner(self, instanceId):
        credentials = LocalhostCredentialsConnector(self.configHolder)
        cloud = CloudConnectorFactory.getCloud(credentials)
        cloud.setEndpointFromParts('localhost', self.configHolder.onePort)
        return cloud.getVmOwner(instanceId)

    def _retrieveInstanceId(self):
        pathElems = self.diskDstPath.split('/')
        instanceId = self._findNumbers(pathElems)
        errorMsg = '%s instance ID in path. ' + 'Path is "%s"' % self.diskDstPath
        if len(instanceId) != 1:
            raise ValueError(errorMsg % ((len(instanceId) == 0) and 'Unable to find'
                                         or 'Too many candidates'))
        return instanceId.pop()

    def _deriveVMOwner(self):
        instanceId = self._retrieveInstanceId()
        owner = self._getVMOwner(instanceId)
        return owner

    def _getDiskOwner(self, pdiskImageId):
        return self.pdisk.getValue(self._OWNER_KEY, pdiskImageId)

    def _getDiskVisibility(self, pdiskImageId):
        return self.pdisk.getValue(self._VISIBILITY_KEY, pdiskImageId)
