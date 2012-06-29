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
from time import time
from os.path import dirname
from getpass import getuser
from urlparse import urlparse

from stratuslab.Util import sshCmdWithOutput, defaultConfigFile
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.Defaults import sshPublicKeyLocation
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Configurator import Configurator
from stratuslab.PersistentDisk import PersistentDisk
from stratuslab.marketplace.Policy import Policy
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
import stratuslab.ManifestInfo as ManifestInfo

class TMCloneCache(object):
    ''' Clone or retrieve from cache disk image
    '''

    # Debug option
    PRINT_TRACE_ON_ERROR = True

    # Position of the provided args
    _ARG_SRC_POS = 1
    _ARG_DST_POS = 2

    _PDISK_PORT = 8445
    
    _UNCOMPRESS_TOOL = {'gz': '/bin/gunzip',
                       'bz2': '/bin/bunzip2'}
    
    _CHECKSUM = 'sha1'
    _CHECKSUM_CMD = '%ssum' % _CHECKSUM
    
    _ACCEPTED_EXTRA_DISK_TYPE = ('DATA_IMAGE_RAW_READONLY', 'DATA_IMAGE_RAW_READ_WRITE')
    _ACCEPTED_ROOT_DISK_TYPE = ('MACHINE_IMAGE_LIVE')
        
    _IDENTIFIER_KEY = 'identifier'
    _COUNT_KEY = 'count'

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

        self._parseArgs(args)
        
        configFile = kwargs.get('conf_filename', defaultConfigFile)
        config = ConfigHolder.configFileToDictWithFormattedKeys(configFile)
        options = PDiskEndpoint.options()
        options.update({'verboseLevel': 0, 'configFile': configFile})
        self.configHolder = ConfigHolder(options, config)
        self.configHolder.assign(self)

        self._initPdiskClient()
        self._initMarketplaceRelated()

        self.defaultSignalHandler = None

    def _initPdiskClient(self):
        self.pdiskEndpoint = self.configHolder.persistentDiskIp
        self.pdiskLVMDevice = self.configHolder.persistentDiskLvmDevice
        self.configHolder.set('pdiskEndpoint', self.pdiskEndpoint)
        self.pdisk = PersistentDisk(self.configHolder)
    
    def _initMarketplaceRelated(self):
        self._retrieveMarketplaceInfos()
        self._initManifestDownloader()

    def _initManifestDownloader(self):
        self.configHolder.set('marketplaceEndpoint', self.marketplaceEndpoint)
        self.manifestDownloader = ManifestDownloader(self.configHolder)

    def run(self):
        self._retrieveDisk()
    
    def _checkArgs(self, args):
        self._assertLength(args, 3, 'Invalid number of arguments')
    
    def _parseArgs(self, args):
        self._checkArgs(args)

        dst = args[self._ARG_DST_POS]
        self.diskDstHost = self._getDiskHost(dst)
        self.diskDstPath = self._getDiskPath(dst)
        self.diskSrc = args[self._ARG_SRC_POS]

    def _retrieveDisk(self):
        if self.diskSrc.startswith('pdisk:'):
            self._startFromPersisted()
        else:
            self._startFromCowSnapshot()
    
    def _startFromPersisted(self):
        diskId = self._getStringPart(self.diskSrc, -1, 4)
        diskType = self.pdisk.getValue('type', diskId)
        
        is_root_disk = self._getDiskIndex(self.diskDstPath) is 0
        if is_root_disk:
            self._checkBootDisk(diskId, diskType)
        elif diskType not in self._ACCEPTED_EXTRA_DISK_TYPE:
            raise ValueError('Only %s type disks can be attached as extra disks'
                             % self._ACCEPTED_EXTRA_DISK_TYPE.join(', '))
        
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
            self._retrieveAndCachePDiskImage()
            
        try:
            self._checkAuthirization()
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
        self._sshPDisk(['curl', '-L', '-o', self.downloadedLocalImageLocation, imageMarketplaceLocation], 
                        'Unable to download "%s"' % imageMarketplaceLocation)
    
    def _uncompressDownloadedImage(self):
        compression = self._getImageCompressionType()
        if not compression:
            if self.downloadedLocalImageLocation.endswith('.gz'):
                raise ValueError('Manifest doesn\'t contain a compression element but ' \
                                 'the location element specified ends with .gz. This is likely ' \
                                 'an error.')
            return
        uncompressTool = self._UNCOMPRESS_TOOL[compression]
        self._sshPDisk([uncompressTool, self.downloadedLocalImageLocation],
                       'Unable to uncompress image')
        self.downloadedLocalImageLocation = self._removeExtension(self.downloadedLocalImageLocation)
        
    def _getImageCompressionType(self):
        compression = self.manifestDownloader.getImageElementValue('compression')
        return compression
    
    def _retrieveDowloadedImageSize(self):
        imageFormat = self._getImageFormat()   
        
        if imageFormat in ManifestInfo.imageFormats:
            self.downloadedLocalImageSize = self._bytesToGiga(int(self._getImageSize()))
        else:
            raise ValueError('Unknown image format: ' + imageFormat)
        
    def _checkDownloadedImageChecksum(self):
        manifestChecksum = self.manifestDownloader.getImageElementValue(self._CHECKSUM)
        computedChecksum = self._sshPDisk([self._CHECKSUM_CMD, self.downloadedLocalImageLocation], 
                                        'Unable to get image checksum')
        computedChecksum = computedChecksum.split(' ')[0]
        if manifestChecksum != computedChecksum:
            raise ValueError('Invalid image checksum, is %s got %s' % (manifestChecksum, computedChecksum))
        
    def _copyDownloadedImageToPartition(self):
        copyCmd = []
        
        if self.configHolder.persistentDiskShare.lower() == 'nfs':
            copyDst = '%s/%s/%s' % (self.configHolder.persistentDiskNfsMountPoint, \
                                    'pdisks', self.pdiskImageId)
            copyCmd = ['cp', self.downloadedLocalImageLocation, copyDst]
        else:
            imageFormat = self._getImageFormat()
            copyDst = '%s/%s' % (self.pdiskLVMDevice, self.pdiskImageId)
            if imageFormat.startswith('qcow'):
                copyCmd = imageFormat.startswith('qcow') and ['cp', '-f', self.downloadedLocalImageLocation, copyDst] 
            else:
                copyCmd = ['dd', 'if=%s' % self.downloadedLocalImageLocation, 'of=%s' % copyDst, 'bs=2048']

        self._sshPDisk(copyCmd, 'Unable to copy image')

    def _getImageFormat(self):
        return self.manifestDownloader.getImageElementValue('format')
        
    def _getImageSize(self):
        return self.manifestDownloader.getImageElementValue('bytes')

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
        elif self.diskSrc.startswith(('pdisk:')): # Ignore Marketplace if pdisk is used
            self.marketplaceEndpoint = None
            self.marketplaceImageId = None
        else: # Local marketplace
            self.marketplaceEndpoint = 'http://localhost'
            try:
                self.marketplaceEndpoint = self.configHolder.marketplaceEndpointLocal
            except:
                pass
            # SunStone adds '<hostname>:' to the image ID
            self.marketplaceImageId = self._getStringPart(self.diskSrc, 1)
        
    def _getMarketplaceEndpointFromURI(self, uri):
        uri_parts = urlparse(uri)
        return '%s://%s/' % (uri_parts.scheme, uri_parts.netloc)

    def _getImageIdFromURI(self, uri):
        fragments = uri.split('/')
        # POP two times if trailing slash
        return fragments.pop() or fragments.pop()

    def _validateMarketplaceImagePolicy(self):
        try:
            self.configHolder.set('marketplaceEndpoint', self.marketplaceEndpoint)
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
        self._sshDst(['/usr/sbin/attach-persistent-disk.sh', diskSrc, self.diskDstPath],
                     'Unable to attach persistent disk to %s' % self.diskDstPath)
    
    def _retrieveAndCachePDiskImage(self):
        self.manifestDownloader.downloadManifestByImageId(self.marketplaceImageId)
        self._validateMarketplaceImagePolicy()
        try:
            self._downloadImage()
            self._uncompressDownloadedImage()
            self._checkDownloadedImageChecksum()
            self._retrieveDowloadedImageSize()
            self._createPDiskFromDowloadedImage()
            self._copyDownloadedImageToPartition()
        except:
            self._deletePDiskSnapshot()
            raise
        finally:
            try:
                self._deleteDownloadedImage()
            except:
                pass
        
    def _createPDiskFromDowloadedImage(self):
        self.pdiskImageId = self.pdisk.createVolume(self.downloadedLocalImageSize, '', False)
        self._setNewPDiskProperties()
    
    def _setNewPDiskProperties(self):
        self._setPDiskInfo(self._IDENTIFIER_KEY, self.marketplaceImageId, self.pdiskImageId)
        self._setPDiskInfo('type', 'MACHINE_IMAGE_ORIGIN', self.pdiskImageId)
        
    def _getPDiskTempStore(self):
        store = self.configHolder.persistentDiskTempStore or '/tmp'
        self._sshDst(['mkdir', '-p', store], 'Unable to create temporary store')
        return store
    
    def _createPDiskSnapshot(self):
        snapshotIdentifier = 'snapshot:%s' % self.pdiskImageId
        self.pdiskSnapshotId = self.pdisk.createCowVolume(self.pdiskImageId, None)
        self._setPDiskIdentifier(snapshotIdentifier, self.pdiskSnapshotId)

    def _checkAuthirization(self):
        pass
    
    def _setSnapshotOwner(self):
        instanceId = self._retrieveInstanceId()
        owner = self._getVMOwner(instanceId)
        self.pdisk.updateVolume({'owner': owner}, self.pdiskSnapshotId)

    def _setPDiskInfo(self, key, value, pdiskId):
        self.pdisk.updateVolume({key: value}, pdiskId)
        
    def _setPDiskIdentifier(self, value, pdiskId):
        self.pdisk.updateVolume({self._IDENTIFIER_KEY: value}, pdiskId)
    
    def _getPDiskSnapshotURL(self):
        return 'pdisk:%s:%s:%s' % (self.pdiskEndpoint, 
                                   self._PDISK_PORT,
                                   self.pdiskSnapshotId)
        
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
            errorMsg = 'Object should have a length of %s%s , got %s' % (length, 
                                                                          atLeast and ' at least' or '', 
                                                                          nbElem)
        if not atLeast and nbElem != length or nbElem < length:
            raise ValueError(errorMsg)
    
    def _bytesToGiga(self, bytesAmout):
        return (bytesAmout / 1024**3) + 1
    
    def _sshDst(self, cmd, errorMsg, dontRaiseOnError=False):
        print 'in _sshDst', cmd
        retCode, output = sshCmdWithOutput(' '.join(cmd), self.diskDstHost, user=getuser(),
                                           sshKey=sshPublicKeyLocation.replace('.pub', ''))
        if not dontRaiseOnError and retCode != 0:
            raise Exception('%s\n: Error: %s' % (errorMsg, output))
        return output
        
    def _sshPDisk(self, cmd, errorMsg, dontRaiseOnError=False):
        print 'in _sshPdisk', cmd
        retCode, output = sshCmdWithOutput(' '.join(cmd), self.pdisk.persistentDiskIp, user=getuser(),
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
