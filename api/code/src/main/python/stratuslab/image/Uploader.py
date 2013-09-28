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
import os.path

import stratuslab.Util as Util
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.Exceptions import ExecutionException
from stratuslab.Signator import Signator
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Compressor import Compressor
from stratuslab.marketplace.Util import Util as MarketplaceUtil
from stratuslab.marketplace.Uploader import Uploader as MarketplaceUploader
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.commandbase.StorageCommand import PDiskEndpoint, PDiskVolume


class Uploader(object):
    @staticmethod
    def buildUploadParser(parser):
        parser.usage = '''usage: %prog [options] <image-file>'''

        parser.add_option('-C', '--compress', dest='compressionFormat',
                          help='Compression format.  One of: %s, none' % ', '.join(Compressor.compressionFormats),
                          default='gz', metavar='FORMAT')

        parser.add_option('--image-only', dest='imageOnly',
                          help='Do not upload metadata file to Marketplace',
                          action='store_true', default=False)

        MarketplaceUtil.addEndpointOption(parser)

        PDiskEndpoint.addOptions(parser)
        PDiskVolume.addOptions(parser)

    @staticmethod
    def checkUploadOptions(options, parser):

        if options.marketplaceEndpoint:
            options.withMarketPlace = True

        if not options.imageOnly:
            MarketplaceUtil.checkEndpointOption(options)

        allowedFormats = list(Compressor.compressionFormats)
        allowedFormats.append('none')

        if options.compressionFormat not in allowedFormats:
            parser.error('Unknown compression format')

        # Do NOT check the validity of the pdisk options, so that the
        # values can be taken from non-pdisk options when necessary.
        # PDiskEndpoint.checkOptions(options)

        # This essentially just checks that the volume tag is acceptable.
        PDiskVolume.checkOptions(options)

    def __init__(self, imageFile, configHolder=ConfigHolder()):
        self.imageMetadata = {}

        self.configHolder = configHolder
        configHolder.assign(self)

        self.imageFile = imageFile
        self.manifestFile = self.imageFile.replace('.img', '.xml')

        self.imageUrl = ''

        self.pdisk = VolumeManagerFactory.create(self.configHolder)

    def start(self):
        Util.printAction('Starting image upload')

        Util.printStep('Compressing image')
        self._compressImage()

        Util.printStep('Uploading image')
        self._uploadImage()

        if not self.imageOnly:
            Util.printAction('Starting manifest upload')

            Util.printStep('Parsing manifest')
            self._parseManifest()

            Util.printStep('Updating manifest')
            self._updateManifest()

            Util.printStep('Signing manifest')
            self._signManifest()

            Util.printStep('Uploading manifest')
            self._uploadMarketplaceManifest()

    def _uploadImage(self):
        self.imageUrl = self.pdisk.uploadVolume(self.imageFile)
        Util.printInfo('Image uploaded: %s' % self.imageUrl)

        self._updateImageMetadataInPDisk()

    def _updateImageMetadataInPDisk(self):
        if self.imageMetadata:
            uuid = self.imageUrl.rsplit('/', 1)[-1]
            self.pdisk.updateVolumeAsUser(self.imageMetadata, uuid)
            Util.printInfo('Image metadata updated: %s' % self.imageMetadata)

    def _updateManifest(self):
        self._addLocationToManifest()
        self._addCompressionFormatToManifest()

    def _signManifest(self):
        configHolder = ConfigHolder(self.__dict__)
        signator = Signator(self.manifestFile, configHolder)
        rc = signator.sign()
        if rc:
            raise ExecutionException('Failed to sign manifest.')
        self.manifestFile = signator.outputManifestFile

    def _execute(self, command):
        if self.verboseLevel <= Util.VERBOSE_LEVEL_NORMAL:
            devNull = open(os.path.devnull, 'w')
            ret = Util.execute(command, stdout=devNull, stderr=devNull)
            devNull.close()
        else:
            ret = Util.execute(command)
        return ret

    def _parseManifest(self):
        manifestInfo = ManifestInfo()
        manifestInfo.parseManifestFromFile(self.manifestFile)

    def _buildManifestName(self, repoFilename):
        return repoFilename.split('.img')[0] + '.xml'

    def _compressFile(self, filename, fmt):

        if fmt.lower() == 'none':
            return filename

        if Compressor.getCompressionFormat(filename) != '':
            Util.printWarning('skipping compression; file appears to already be compressed')
            return filename

        compressionCmd = Compressor._getCompressionCommandByFormat(fmt)

        compressedFilename = '%s.%s' % (filename, fmt)
        if os.path.isfile(compressedFilename):
            Util.printWarning('Compressed file %s already exists, skipping' % compressedFilename)
            return compressedFilename

        if not os.path.exists(filename):
            Util.printError('Missing file: ' + filename, exit=True)

        ret = self._execute([compressionCmd, filename])
        if ret != 0:
            Util.printError('Error compressing file: %s' % compressedFilename, exit=True)

        return compressedFilename

    def _compressImage(self):
        self.imageFile = self._compressFile(self.imageFile, self.compressionFormat)

    def _addCompressionFormatToManifest(self):
        if self.compressionFormat.lower() != 'none':
            ManifestInfo.addElementToManifestFile(self.manifestFile,
                                                  'compression', self.compressionFormat)
        else:
            Util.printWarning("'none' specified for compression; manifest compression element NOT updated")

    def _addLocationToManifest(self):
        ManifestInfo.addElementToManifestFile(self.manifestFile,
                                              'location', self.imageUrl)

    def _uploadMarketplaceManifest(self):
        uploader = MarketplaceUploader(self.configHolder)
        url = uploader.upload(self.manifestFile)
        Util.printInfo('Manifest uploaded: %s' % url)
