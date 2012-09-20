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
from stratuslab.PersistentDisk import PersistentDisk
from stratuslab.commandbase.StorageCommand import PDiskEndpoint

etree = Util.importETree()

class Uploader(object):

    @staticmethod
    def buildUploadParser(parser):
        parser.usage = '''usage: %prog [options] <image-file>'''

        parser.add_option('-C', '--compress', dest='compressionFormat',
                help='Compression format',
                default='gz', metavar='FORMAT')

        parser.add_option('--list-compression', dest='listCompressionFormat',
                help='List available compression formats',
                default=False, action='store_true')

        parser.add_option('--image-only', dest='imageOnly',
                help='Do not upload metadata file to Marketplace',
                action='store_true', default=False)

        MarketplaceUtil.addEndpointOption(parser)

        PDiskEndpoint.addOptions(parser)

    @staticmethod
    def checkUploadOptions(options, parser):

        if options.marketplaceEndpoint:
            options.withMarketPlace = True

        MarketplaceUtil.checkEndpointOption(options)

        if options.compressionFormat not in Compressor.compressionFormats:
            parser.error('Unknown compression format')
        
        PDiskEndpoint.checkOptionsRaiseOnError(options)

    def __init__(self, imageFile, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        configHolder.assign(self)

        self.imageFile = imageFile
        self.manifestFile = self.imageFile.replace('.img', '.xml')

        self.imageUrl = ''

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
            self._uploadMarketPlaceManifest()

    def _uploadImage(self):
        pdisk = PersistentDisk(self.configHolder)
        self.imageUrl = pdisk.uploadVolume(self.imageFile)
        print "Image uploaded: %s" % self.imageUrl 

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
            devNull = open('/dev/null', 'w')
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

    def _compressFile(self, filename, format):
        compressionCmd = Compressor._getCompressionCommandByFormat(format)

        compressedFilename = '%s.%s' % (filename, format)
        if os.path.isfile(compressedFilename):
            Util.printWarning('Compressed file %s already exists, skipping' % compressedFilename)
            return compressedFilename

        if not os.path.exists(filename):
            Util.printError('Missing file: ' + filename, exit=True)

        ret = self._execute([compressionCmd, filename])
        if ret != 0:
            Util.printError('Error compressing file: ' % compressedFilename, exit=True)

        return compressedFilename

    def _compressImage(self):
        self.imageFile = self._compressFile(self.imageFile, self.compressionFormat)

    def _addCompressionFormatToManifest(self):
        ManifestInfo.addElementToManifestFile(self.manifestFile, 
                                          'compression', self.compressionFormat)

    def _addLocationToManifest(self):
        ManifestInfo.addElementToManifestFile(self.manifestFile, 
                                              'location', self.imageUrl)

    def _uploadMarketPlaceManifest(self):
        uploader = MarketplaceUploader(self.configHolder)
        url = uploader.upload(self.manifestFile)
        print "Manifest uploaded: %s" % url

