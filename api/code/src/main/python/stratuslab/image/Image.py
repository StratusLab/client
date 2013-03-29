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
import re

import stratuslab.Exceptions as Exceptions
import stratuslab.Util as Util
from stratuslab.Compressor import Compressor
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.ManifestInfo import ManifestInfo

class Image(object):

    re_imageId = re.compile('^[A-Za-z0-9_-]{27}$')
    re_diskId = re.compile('^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.configHolder = configHolder

        self.manifestDownloader = self._createDownloader()

    def _createDownloader(self):
        configHolder = self.configHolder.copy()
        return ManifestDownloader(configHolder)
    
    def checkImageExists(self, imageId):
        """dereferences the entry and checks the image location if an image id"""
        if Image.isImageId(imageId):
            self._checkImageByIdInMarketplace(imageId)

    @staticmethod
    def checksumImage(filename, checksums=ManifestInfo.MANDATORY_CHECKSUMS):
        """Return dictionary of checksums."""

        return Compressor.checksum_file(filename, checksums)

    @staticmethod
    def isImageId(imageId):
        return Image.re_imageId.match(imageId)

    @staticmethod
    def isDiskId(diskId):
        return Image.re_diskId.match(diskId)

    def getImageFormatByImageId(self, imageId):
        return self._getImageElementValue('format', imageId)

    def getImageDisksBusTypeByImageId(self, imageId):
        return self._getImageElementValue('disks-bus', imageId)

    def getInboundPortsByImageId(self, imageId):
        return self._getImageElementValue('inboundports', imageId)

    def _getImageElementValue(self, element, imageId):
        if Image.isImageId(imageId):
            return self.manifestDownloader.getImageElementValue(element, imageId)
        else:
            raise Exceptions.ValidationException('Image ID was expected. Given %s' % imageId)
            
    def _checkImageByUrl(self, imageUrl):
        try:
            Util.checkUrlExists(imageUrl)
        except (Exceptions.ValidationException, Exceptions.ExecutionException), ex:
            raise Exceptions.ValidationException("Unable to access image '%s': %s" %
                                      (imageUrl, str(ex)))
        else:
            self.printDetail('Image available: %s' % imageUrl)

    def _checkImageByIdInMarketplace(self, imageId):
        imageLocations = self._getImageLocationsByImageId(imageId)
        if not imageLocations:
            raise Exceptions.ValidationException('Image location(s) are not set in manifest for the image with ID %s' % imageId)
        else:
            self.printDetail('Manifest with ID %s is available. Image locations: %s' % 
                             (imageId, str(imageLocations)))

    def _getImageLocationsByImageId(self, imageId):
        '''Return list of locations.'''
        self.manifestDownloader.downloadManifestByImageId(imageId)
        return self.manifestDownloader.getImageLocations()

    def printDetail(self, msg):
        return Util.printDetail(msg, self.verboseLevel, Util.VERBOSE_LEVEL_DETAILED)
