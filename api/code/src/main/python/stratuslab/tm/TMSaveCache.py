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
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.vm_manager.vm_manager import VmManager
from stratuslab.marketplace.Uploader import Uploader
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.commandbase.StorageCommand import PDiskEndpoint
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.messaging.EmailClient import EmailClient
from stratuslab.installator.PersistentDisk import PersistentDisk as PDiskInstaller
import stratuslab.Util as Util
from stratuslab.Exceptions import ConfigurationException
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
    _SEED_KEY = 'seed'

    def __init__(self, args, **kwargs):
        self.args = args

        self.diskSrcPath = None
        self.diskSrcHost = None
        self.vmDir = None
        self.diskName = None
        self.persistentDiskPublicBaseUrl = None
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

        self.builtImageValidityPeriod = None

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

        if not self.persistentDiskPublicBaseUrl:
            pdisk = VolumeManagerFactory.create(self.configHolder)
            pdisk._buildFQNEndpoint()
            self.persistentDiskPublicBaseUrl = Util.getProtoHostnamePortFromUri(pdisk.endpoint)

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
        self.pdiskPath = self._updatePDiskIpForNewImageUri(uris[0])
        self.diskName = self._getDiskNameFromURI(uris[0])

    def _getAttachedVolumeURIs(self):
        register_filename_contents = self._sshDst(['/usr/sbin/stratus-list-registered-volumes.py',
                                                   '--vm-id', str(self.instanceId)],
                                                  'Unable to get registered volumes')
        return register_filename_contents.splitlines()

    def _updatePDiskIpForNewImageUri(self, pdisk_image_uri):
        """pdisk_image_uri is assumed to be in the form pdisk:<ip>:<port>:<uuid>
        as returned by TMSaveCache._getAttachedVolumeURIs()"""
        pdisk_hostport_list = Util.getHostnamePortFromUri(self.persistentDiskPublicBaseUrl).split(':')
        pdisk_image_uri_list = pdisk_image_uri.split(':')
        pdisk_image_uri_list[1:len(pdisk_hostport_list) + 1] = pdisk_hostport_list
        return ':'.join(pdisk_image_uri_list)

    def _getDiskNameFromURI(self, uri):
        return uri.split(':')[-1]

    def _getPDiskHostPortFromURI(self, uri):
        splittedUri = uri.split(':')
        self._assertLength(splittedUri, 4)
        return ':'.join(splittedUri[1:3])

    def _detachAllVolumes(self):
        pdisk = VolumeManagerFactory.create(self.configHolder)
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
        pdisk = VolumeManagerFactory.create(self.configHolder)
        self.createdPDiskId = pdisk.rebaseVolume(self.diskName)

    def _updateVolumeIdentifier(self):
        pdisk = VolumeManagerFactory.create(self.configHolder)
        pdiskOwner = self._getPdiskOwner()
        pdisk.updateVolume({self._IDENTIFIER_KEY: self.snapshotMarketplaceId,
                            self._OWNER_KEY: pdiskOwner,
                            self._SEED_KEY: 'on',
                            self._TAG_KEY: self._getTitle()},
                            self.createdPDiskId)
        
    def _getPdiskOwner(self):
        "pdisk volume owner is the owner of the VM."
        return self.cloud.getVmOwner(self.instanceId)

    def _getTitle(self):
        try:
            return self.createImageInfo[VmManager.CREATE_IMAGE_KEY_NEWIMAGE_TITLE]
        except KeyError:
            return ""

    #--------------------------------------------
    # Marketplace and related
    #--------------------------------------------

    def _generateManifest(self):
        self._update_endroser_cert_and_image_validity_periods()
        self._generateP12Cert()
        self._createManifest()

    def _createManifest(self):
        self._retrieveManifestsPath()
        self.pdiskPathNew = self._buildPDiskPath(self.createdPDiskId)
        self._buildAndSignManifest()

    def _update_endroser_cert_and_image_validity_periods(self):
        try:
            self._P12_VALIDITY = int(self.builtImageValidityPeriod)
            self._IMAGE_VALIDITY = self._P12_VALIDITY * 24 * 3600
        except TypeError:
            pass

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
        manifest_info.creator = self.createImageInfo[VmManager.CREATE_IMAGE_KEY_CREATOR_NAME]
        manifest_info.version = self.createImageInfo[VmManager.CREATE_IMAGE_KEY_NEWIMAGE_VERSION] or \
                                Util.incrementMinorVersionNumber(manifest_info.version)
        manifest_info.title = self._getTitle()
        manifest_info.comment = self.createImageInfo[VmManager.CREATE_IMAGE_KEY_NEWIMAGE_COMMENT]
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
        iscsi_type = self._configPdiskGetIscsiBackendType().lower()
        if iscsi_type in ('netapp', 'ceph'):
            return self._getSnapshotChecksumFromAttachedDevice()
        elif iscsi_type == 'lvm':
            return self._getSnapshotChecksum_Lvm()
        else:
            raise ConfigurationException('Unknown iSCSI backend type: %s' % iscsi_type)

    def _getSnapshotChecksumFromAttachedDevice(self):

        PDISK_BACKEND_CMD = '/usr/sbin/persistent-disk-backend.py'

        PDISK_CLIENT_CMD = '/usr/sbin/stratus-pdisk-client.py'

        PDISK_ID = 'pdisk:localhost:8445:%s' % self.diskName

        def _mapDisk():
            # LUN mapping might be needed
            netapp_map = [PDISK_BACKEND_CMD,
                          '--action', 'map',
                          self.diskName]
            self._ssh(self.persistentDiskIp, netapp_map,
                      'Failed to map %s on NetApp' % self.diskName,
                      dontRaiseOnError=True)

        def _getTURL():
            # Get TURL
            get_turl_cmd = [PDISK_BACKEND_CMD,
                            '--action', 'getturl',
                            self.diskName]
            return self._ssh(self.persistentDiskIp, get_turl_cmd,
                             'Failed to get TURL for %s' % self.diskName)

        def _attachLUN(turl):
            snapshotPath = os.path.join('/var/tmp/stratuslab',
                                        self.diskName + '.link')
            # Attach LUN and link to a known location
            backend_type = self._configPdiskGetIscsiBackendType().lower()
            if backend_type == 'netapp':
                portal = Util.getHostnameFromUri(turl) 
                discover_cmd = ['sudo', 'iscsiadm', '-m', 'discovery', '-t', 'sendtargets', '-p', portal]
                self._ssh(self.persistentDiskIp, discover_cmd,
                          'Failed discovering iSCSI targets.')
            attach_and_link_cmd = ['sudo', PDISK_CLIENT_CMD,
                                   '--op', 'up',
                                   '--attach',
                                   '--pdisk-id', PDISK_ID,
                                   '--link-to', snapshotPath,
                                   '--turl', turl]
            self._ssh(self.persistentDiskIp, attach_and_link_cmd,
                      'Failed attaching %s to %s' % (PDISK_ID, self.persistentDiskIp))
            return snapshotPath

        def _checksumSnapshot(snapshotPath):
            checksumOutput = self._ssh(self.persistentDiskIp, ['sudo', self._CHECKSUM_CMD, snapshotPath],
                                       'Unable to compute checksum of "%s"' % snapshotPath)
            return checksumOutput.split(' ')[0]

        def _clenup(snapshotPath):
            # Unmount
            detach_lun_cmd = ['sudo', PDISK_CLIENT_CMD,
                              '--op', 'down',
                              '--attach',
                              '--pdisk-id', PDISK_ID,
                              '--turl', turl]
            self._ssh(self.persistentDiskIp, detach_lun_cmd,
                      'Failed detaching %s from %s' % (PDISK_ID, self.persistentDiskIp))
            # Remove link
            self._ssh(self.persistentDiskIp, ['sudo', 'rm', '-f', snapshotPath],
                      'Failed to remove link to %s on %s' % (self.diskName, self.persistentDiskIp),
                      dontRaiseOnError=True)

        _mapDisk()
        turl = _getTURL()
        snapshotPath = _attachLUN(turl)
        checksum = _checksumSnapshot(snapshotPath)
        _clenup(snapshotPath)

        return checksum

    def _getSnapshotChecksum_Lvm(self):
        snapshotPath = self._getSnapshotPath()
        checksumOutput = self._ssh(self.persistentDiskIp, [self._CHECKSUM_CMD, snapshotPath],
                                   'Unable to compute checksum of "%s"' % snapshotPath)
        printInfo('persistent disk IP: "%s"' % self.persistentDiskIp)
        printInfo('snapshot path: "%s"' % snapshotPath)
        printInfo('checksum output is: "%s"' % checksumOutput)
        return checksumOutput.split(' ')[0]

    def _configPdiskGetIscsiBackendType(self):
        conf = ConfigHolder.configFileToDict(PDiskInstaller.pdiskConfigBackendFile)
        return conf.get('type')

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
        
    def _getRemoteFileContent(self, host, fn):
        return self._ssh(host, ['cat', fn], 
                         "Failed to get content of '%s' from host '%s'." % (fn, host))

    def _getRemoteFileAsFileHandler(self, host, fn):
        import StringIO
        fh = StringIO.StringIO()
        content = self._getRemoteFileContent(host, fn)
        fh.write(content)
        fh.seek(0)
        return fh

    def _getRemoteConfFileAsDict(self, host, conf_file):
        fh = self._getRemoteFileAsFileHandler(host, conf_file)
        return ConfigHolder.configFileHandlerToDict(fh)

    def _getSnapshotPath(self):
        conf = self._getRemoteConfFileAsDict(self.persistentDiskIp, 
                                             PDiskInstaller.pdiskConfigBackendFile)
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

    def _ssh(self, host, cmd, errorMsg, dontRaiseOnError=False, sshQuiet=True):
        retCode, output = sshCmdWithOutput(' '.join(cmd), host, user=getuser(),
                                           sshKey=sshPublicKeyLocation.replace('.pub', ''),
                                           sshQuiet=sshQuiet)
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
        if not self.createImageInfo[VmManager.CREATE_IMAGE_KEY_CREATOR_EMAIL]:
            return

        configHolder = self.configHolder.copy()
        configHolder.set('subject', 'New image created %s' % self.snapshotMarketplaceId)
        configHolder.set('recipient', self.createImageInfo[VmManager.CREATE_IMAGE_KEY_CREATOR_EMAIL])
        configHolder.set('sender', self.saveImageReplyToEmail)

        emailClient = EmailClient(configHolder)
        emailClient.send(self._emailText(),
                         attachment=self.manifestNotSignedPath)

    def _publishImageId(self):
        msg_type = self.createImageInfo.get(VmManager.CREATE_IMAGE_KEY_MSG_TYPE, '')
        if not msg_type:
            return

        configHolder = self.configHolder.copy()
        configHolder.set('msg_type', msg_type)
        configHolder.set('msg_endpoint',
                         self.createImageInfo.get(VmManager.CREATE_IMAGE_KEY_MSG_ENDPOINT, ''))
        configHolder.set('msg_queue',
                         self.createImageInfo.get(VmManager.CREATE_IMAGE_KEY_MSG_QUEUE, ''))

        message = self.createImageInfo.get(VmManager.CREATE_IMAGE_KEY_MSG_MESSAGE, '{}')

        ImageIdPublisher(message,
                         self.snapshotMarketplaceId,
                         configHolder).publish()

    def _emailText(self):
        return """
The image creation was SUCCESSFUL.  The image has an ID of
%(snapshotMarketplaceId)s.

It is stored in the persistent disks service.  By default, the image 
is private and can only be accessed/launched by the image creator.  
You can change the access policy by visiting the links below
%(persistentDiskPublicBaseUrl)s/pswd/disks/%(pdiskId)s
%(persistentDiskPublicBaseUrl)s/cert/disks/%(pdiskId)s 

A draft image manifest entry has been generated and is attached to
this message.  It has also been uploaded to %(marketplace)s.  The
validity of this entry is only %(imageValidity)s days!

To provide a longer validity period you must:
1) edit the attached manifest, updating the validity period,
2) sign the manifest with the stratus-sign-metadata command, and
3) upload the manifest to the Marketplace.

The manifest can be uploaded either via the Marketplace's web
interface or via the command stratus-upload-metadata.

Cheers.
        """ % {'persistentDiskPublicBaseUrl': self.persistentDiskPublicBaseUrl,
               'pdiskId': self.createdPDiskId,
               'snapshotMarketplaceId': self.snapshotMarketplaceId,
               'marketplace': self.targetMarketplace,
               'imageValidity': self._P12_VALIDITY}

    def _emitNewImageInfo(self):
        """To be able to recover image ID from log file by image creation test."""
        printInfo("INFO: %s: MARKETPLACE_AND_IMAGEID %s %s" % (os.path.basename(self.args[0]),
                                                               self.targetMarketplace,
                                                               self.snapshotMarketplaceId))
