#!/usr/bin/env python
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
import shutil
from string import ascii_uppercase, digits
from random import choice
from os.path import dirname
from getpass import getuser
from tempfile import mkstemp, mkdtemp

from stratuslab.Signator import Signator
from stratuslab.Util import defaultConfigFile, sshCmdWithOutput, printInfo, printError
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.Defaults import sshPublicKeyLocation
from stratuslab.Defaults import marketplaceEndpoint
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.CertGenerator import CertGenerator
from stratuslab.PersistentDisk import PersistentDisk
from stratuslab.marketplace.Uploader import Uploader
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.messaging.EmailClient import EmailClient
from stratuslab.installator.PersistentDisk import PersistentDisk as PDiskInstaller
import stratuslab.Util as Util
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Runner import Runner
from stratuslab.messaging.MessagePublishers import ImageIdPublisher


class TMSaveCache(object):
    """Save a running VM image in PDisk"""

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSE_LEVEL = 0

    # Position of the provided args
    _ARG_SRC_POS = 1
    _ARG_DST_POS = 2

    _PDISK_PORT = 8445
    _P12_VALIDITY = 2

    _IMAGE_VALIDITY = _P12_VALIDITY * 24 * 3600

    _CHECKSUM = 'sha1'
    _CHECKSUM_CMD = '%ssum' % _CHECKSUM

    _IDENTIFIER_KEY = 'identifier'
    _OWNER_KEY = 'owner'
    _TAG_KEY = 'tag'

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
        self.manifestTempDir = ''
        self.manifestPath = None
        self.manifestNotSignedPath = None
        self.pdiskEndpoint = None
        self.pdiskPath = None
        self.pdiskPathNew = None
        self.originImageIdUrl = None
        self.originImageId = None
        self.originMarketPlace = None
        self.instanceId = None
        self.imageSha1 = None
        self.createImageInfo = None
        self.cloud = None

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

        # TODO: support instance migration

        self._checkArgs()
        self._parseArgs()
        self._retrieveInstanceId()
        self._retrieveVmDir()
        self._retrieveAttachedVolumeInfo()
        self._detachAllVolumes()
        self._retrieveSnapshotId()
        self._retrieveOriginImageInfo()
        self._rebaseSnapshot()
        self._retrieveCreateImageInfo()
        self._generateManifest()
        self._updateVolumeIdentifier()
        self._retrieveTargetMarketplace()
        self._uploadManifest()
        self._notify()

        # for testability
        self._emitNewImageInfo()

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
        if len(self.args) != 3:
            raise ValueError('Invalid number of arguments')

    def _parseArgs(self):
        src = self.args[self._ARG_SRC_POS]
        self.diskSrcPath = self._getDiskPath(src)
        self.diskSrcHost = self._getDiskHost(src)

    #--------------------------------------------
    # Persistent disk and related
    #--------------------------------------------

    def _retrieveAttachedVolumeInfo(self):
        uris = self._getAttachedVolumeURIs()
        self.attachedVolumeURIs = uris

        # copy out the information for the first disk in the list
        # this will be the one used when saving a new image
        self.pdiskPath = uris[0]
        self.diskName = self._getDiskNameFromURI(uris[0])

    def _getAttachedVolumeURIs(self):
        register_filename_contents =  self._sshDst(['/usr/sbin/stratus-list-registered-volumes.py',
                                                    '--vm-id',  str(self.instanceId)],
                                                   'Unable to get registered volumes')
        return register_filename_contents.splitlines()

    def _getDiskNameFromURI(self, uri):
        return uri.split(':')[-1]

    def _getPDiskHostPortFromURI(self, uri):
        splittedUri = uri.split(':')
        self._assertLength(splittedUri, 4)
        return ':'.join(splittedUri[1:3])

    def _detachAllVolumes(self):
        pdisk = PersistentDisk(self.configHolder)
        msg = ''
        for pdisk_uri in self.attachedVolumeURIs:
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

    def _retrieveOriginImageInfo(self):
        vmSource = self.cloud.getVmDiskSource(self.instanceId, 0)
        self.originImageIdUrl = vmSource
        self.originImageId = vmSource.split('/')[-1]
        self.originMarketPlace = '/'.join(vmSource.split('/')[:-2])

    def _rebaseSnapshot(self):
        pdisk = PersistentDisk(self.configHolder)
        self.createdPDiskId = pdisk.rebaseVolume(self.diskName)

    def _updateVolumeIdentifier(self):
        pdisk = PersistentDisk(self.configHolder)
        pdiskOwner = pdisk.getValue(self._OWNER_KEY, self.diskName)
        pdisk.updateVolume({self._IDENTIFIER_KEY: self.snapshotMarketplaceId,
                            self._OWNER_KEY: pdiskOwner,
                            self._TAG_KEY: self._getTitle()},
                           self.createdPDiskId)

    def _getTitle(self):
        try:
            return self.createImageInfo[Runner.CREATE_IMAGE_KEY_NEWIMAGE_TITLE]
        except KeyError:
            return ""

    #--------------------------------------------
    # Marketplace and related
    #--------------------------------------------

    def _generateManifest(self):
        self._generateP12Cert()
        self._createManifest()

    def _createManifest(self):
        self._retrieveManifestsPath()
        self.pdiskPathNew = self._buildPDiskPath(self.createdPDiskId)
        self._buildAndSignManifest()

    def _retrieveManifestsPath(self):
        self._createManifestTempDir()
        self.manifestPath = '%s/manifest.xml' % self.manifestTempDir
        self.manifestNotSignedPath = '%s/manifest-not-signed.xml' % self.manifestTempDir

    def _createManifestTempDir(self):
        self.manifestTempDir = mkdtemp(prefix='manifest-')

    def _retrieveCreateImageInfo(self):
        self.createImageInfo = self.cloud.getCreateImageInfo(self.instanceId)

    def _buildAndSignManifest(self):
        self._buildAndSaveManifest()
        self._signManifest()

    def _buildAndSaveManifest(self):

        manifest_downloader = ManifestDownloader(self.configHolder)
        manifest_info = manifest_downloader.getManifestInfo(self.originImageIdUrl)

        manifest_info.sha1 = self.imageSha1
        manifest_info.creator = self.createImageInfo[Runner.CREATE_IMAGE_KEY_CREATOR_NAME]
        manifest_info.version = self.createImageInfo[Runner.CREATE_IMAGE_KEY_NEWIMAGE_VERSION] or \
                                Util.incrementMinorVersionNumber(manifest_info.version)
        manifest_info.title = self._getTitle()
        manifest_info.comment = self.createImageInfo[Runner.CREATE_IMAGE_KEY_NEWIMAGE_COMMENT]
        manifest_info.locations = [self.pdiskPathNew]
        manifest_info.IMAGE_VALIDITY = self._IMAGE_VALIDITY

        manifest_info.buildAndSave(self.manifestNotSignedPath)

        self.snapshotMarketplaceId = manifest_info.identifier

    def _signManifest(self):

        self.configHolder.set('outputManifestFile', self.manifestPath)
        self.configHolder.set('p12Certificate', self.p12cert)
        self.configHolder.set('p12Password', self.p12pswd)

        signator = Signator(self.manifestNotSignedPath, self.configHolder)
        rc = signator.sign()
        if rc != 0:
            printError("Error signing metadata.")

    def _uploadManifest(self):
        uploader = Uploader(self.configHolder)
        uploader.marketplaceEndpoint = self.targetMarketplace
        uploader.upload(self.manifestPath)

    def _retrieveSnapshotId(self):
        self.imageSha1 = self._getSnapshotSha1()

    def _getSnapshotSha1(self):
        snapshotPath = self._getSnapshotPath()
        checksumOutput = self._ssh(self.persistentDiskIp, [self._CHECKSUM_CMD, snapshotPath],
                                   'Unable to compute checksum of "%s"' % snapshotPath)
        printInfo('persistent disk IP: "%s"' % persistentDiskIp)
        printInfo('snapshot path: "%s"' % snapshotPath)
        printInfo('checksum output is: "%s"' % checksumOutput)
        return checksumOutput.split(' ')[0]

    def _retrieveTargetMarketplace(self):
        if self.createImageInfo.get('NEWIMAGE_MARKETPLACE'):
            self.targetMarketplace = self.createImageInfo['NEWIMAGE_MARKETPLACE']
        else:
            self.targetMarketplace = getattr(self.configHolder,
                                             'marketplaceEndpointLocal',
                                             self.originMarketPlace)

        if not self.targetMarketplace:
            self.targetMarketplace = marketplaceEndpoint

    #--------------------------------------------
    # Utility
    #--------------------------------------------

    def _buildPDiskPath(self, imageId):
        return ':'.join(self.pdiskPath.split(':')[:-1] + [imageId, ])

    def _assertLength(self, elem, size):
        if len(elem) != size:
            raise ValueError('List should have %s element(s), got %s' % (size, len(elem)))

    def _randomString(self, size=6):
        chars = ascii_uppercase + digits
        return ''.join(choice(chars) for _ in range(size))

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

    def _getSnapshotPath(self):
        conf = ConfigHolder.configFileToDict(PDiskInstaller.pdiskConfigBackendFile)
        key = 'volume_name'
        try:
            volume_path = conf[key]
        except:
            raise ConfigurationException("Failed to get "
                                         "'%s' from configuration file: %s" %
                                         (key, PDiskInstaller.pdiskConfigBackendFile))
        return os.path.join(volume_path, self.diskName)

    def _removeCarriageReturn(self, string):
        return string.replace('\r', '').replace('\n', '')

    def _sshDst(self, cmd, errorMsg, dontRaiseOnError=False):
        return self._ssh(self.diskSrcHost, cmd, errorMsg, dontRaiseOnError)

    def _ssh(self, host, cmd, errorMsg, dontRaiseOnError=False):
        retCode, output = sshCmdWithOutput(' '.join(cmd), host, user=getuser(),
                                           sshKey=sshPublicKeyLocation.replace('.pub', ''))
        if not dontRaiseOnError and retCode != 0:
            raise Exception('%s\n: Error: %s' % (errorMsg, output))
        return output

    def _generateP12Cert(self):
        self.p12cert = mkstemp('.p12', 'cert-')[1]
        self.p12pswd = self._randomString()
        configHolder = self.configHolder.copy()
        configHolder.set('commonName', 'Jane Tester')
        configHolder.set('outputFile', self.p12cert)
        configHolder.set('certPassword', self.p12pswd)
        configHolder.set('certValidity', self._P12_VALIDITY)
        configHolder.set('subjectEmail', 'jane.tester@example.org')
        configHolder.set('noCleanup', False)
        CertGenerator(configHolder).generateP12()

    def _cleanup(self):
        self._removeTempFilesAndDirs()

    def _removeTempFilesAndDirs(self):
        shutil.rmtree(self.manifestTempDir, ignore_errors=True)
        try:
            os.unlink(self.p12cert)
        except:
            pass

    def _notify(self):
        self._sendEmailToUser()
        self._publishImageId()

    def _sendEmailToUser(self):
        if not self.createImageInfo[Runner.CREATE_IMAGE_KEY_CREATOR_EMAIL]:
            return

        configHolder = self.configHolder.copy()
        configHolder.set('subject', 'New image created %s' % self.snapshotMarketplaceId)
        configHolder.set('recipient', self.createImageInfo[Runner.CREATE_IMAGE_KEY_CREATOR_EMAIL])

        emailClient = EmailClient(configHolder)
        emailClient.send(self._emailText(),
                         attachment=self.manifestNotSignedPath)

    def _publishImageId(self):
        msg_type = self.createImageInfo.get(Runner.CREATE_IMAGE_KEY_MSG_TYPE, '')
        if not msg_type:
            return

        configHolder = self.configHolder.copy()
        configHolder.set('msg_type', msg_type)
        configHolder.set('msg_endpoint',
                         self.createImageInfo.get(Runner.CREATE_IMAGE_KEY_MSG_ENDPOINT, ''))
        configHolder.set('msg_queue',
                         self.createImageInfo.get(Runner.CREATE_IMAGE_KEY_MSG_QUEUE, ''))

        message = self.createImageInfo.get(Runner.CREATE_IMAGE_KEY_MSG_MESSAGE, '{}')

        ImageIdPublisher(message,
                         self.snapshotMarketplaceId,
                         configHolder).publish()

    def _emailText(self):
        return """
Image creation was successful.
New image was stored in local PDISK service
https://%(pdiskHostPort)s/cert/disks/%(pdiskId)s
https://%(pdiskHostPort)s/pswd/disks/%(pdiskId)s
Image manifest with ID %(snapshotMarketplaceId)s was signed with dummy certificate and uploaded to %(marketplace)s.
Alternatively, you can sign attached manifest and upload to Marketplace with:
stratus-sign-metadata <manifest file>
stratus-upload-metadata <manifest file>

NB! The validity of the manifest is %(imageValidity)s hours. Please change it!

The validity of the signing certificate is %(p12Validity)s days.

Cheers.
        """ % {'pdiskHostPort': self.pdiskHostPort,
               'pdiskId': self.createdPDiskId,
               'snapshotMarketplaceId': self.snapshotMarketplaceId,
               'marketplace': self.targetMarketplace,
               'p12Validity': self._P12_VALIDITY,
               'imageValidity': self._P12_VALIDITY * 24}

    def _emitNewImageInfo(self):
        """To be able to recover image ID from log file by image creation test."""
        printInfo("INFO: %s: MARKETPLACE_AND_IMAGEID %s %s" % (os.path.basename(self.args[0]),
                                                               self.targetMarketplace,
                                                               self.snapshotMarketplaceId))
