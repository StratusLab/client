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
import tempfile

from stratuslab import Util
from stratuslab import Defaults
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.Compressor import Compressor
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import InputException

from stratuslab.marketplace.ImageValidator import ImageValidator
from stratuslab.marketplace.ManifestValidator import ManifestValidator
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader

etree = Util.importETree()


class Downloader(object):
    ENDPOINT = Defaults.marketplaceEndpoint
    LOCAL_IMAGE_FILENAME = '/tmp/image.img'

    def __init__(self, configHolder=ConfigHolder()):
        self.localImageFilename = ''
        self.configHolder = configHolder
        self.imageUrl = ''
        self.compression = ''
        self.marketplaceEndpoint = Downloader.ENDPOINT

        configHolder.assign(self)

        self.localImageFilename = os.path.abspath(self.localImageFilename)
        self.manifestObject = None

    def download(self, uri):
        """uri is the full resource uri uniquely identifying a single manifest entry"""
        tempMetadataFilename = tempfile.mktemp()
        ManifestDownloader(self.configHolder).getManifestAsFile(uri, tempMetadataFilename)
        manifestInfo = ManifestInfo(self.configHolder)

        manifestInfo.parseManifestFromFile(tempMetadataFilename)

        tempImageFilename = self._downloadFromLocations(manifestInfo)
        self._verifySignature(tempImageFilename, tempMetadataFilename)

        tempImageFilename = self._inflateImage(tempImageFilename)
        if not os.path.exists(tempImageFilename):
            raise InputException('Failed to find image matching image resource uri: %s' % uri)

        self._verifyHash(tempImageFilename, manifestInfo.sha1)

        shutil.copy2(tempImageFilename, self.localImageFilename)

        os.remove(tempImageFilename)
        os.remove(tempMetadataFilename)

        return self.localImageFilename

    def _downloadFromLocations(self, manifestInfo):
        tempImageFilename = ''
        for location in manifestInfo.locations:
            self._printDetail('Looking for image: %s' % location)
            try:
                tempImageFilename = self._downloadImage(location)
                break
            except KeyboardInterrupt:
                raise
            except:
                pass

        return tempImageFilename

    def _downloadImage(self, url):
        compressionExtension = self._extractCompressionExtension(url)

        localFilename = tempfile.mktemp()
        localImageName = localFilename + compressionExtension

        Util.wget(url, localImageName)

        return localImageName

    def _extractCompressionExtension(self, url):
        compression = url.split('.')[-1]

        if compression in Compressor.compressionFormats:
            return '.' + compression
        else:
            return ''

    def _verifySignature(self, imageFilename, metadataFilename):
        ManifestValidator(self.configHolder).verifySignature(imageFilename, metadataFilename)

    def _inflateImage(self, imageFilename):
        extension = self._extractCompressionExtension(imageFilename)
        inflatedFilename = imageFilename
        if extension:
            self._printDetail('Inflating image %s' % imageFilename)
            Compressor.inflate(imageFilename)
            inflatedFilename = imageFilename[:-len(extension)]

        return inflatedFilename

    def _verifyHash(self, imageFilename, hashFromManifest):
        ImageValidator().verifyHash(imageFilename, hashFromManifest)

    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, Util.VERBOSE_LEVEL_NORMAL)
