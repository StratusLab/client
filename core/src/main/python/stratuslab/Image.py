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

from stratuslab.marketplace.Downloader import Downloader
import stratuslab.Exceptions as Exceptions
import stratuslab.Util as Util

class Image(object):
    
    re_imageUrl = re.compile('http[s]?://.*\.(img|qco|qcow|qcow2)\.?(gz|bz2)?$')

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.configHolder = configHolder

        self.downloader = None
    
    def checkImageExists(self, image):
        """image - URL or image ID"""

        if Image.isImageUrl(image):
            imageUrl = image
            self._checkImageByUrl(imageUrl)
        else:
            imageId = image
            self._checkImageByIdInMarketplace(imageId)

    @staticmethod
    def isImageUrl(imageReference):
        return Image.re_imageUrl.match(imageReference)

    def getImageFormatByImageId(self, imageId):
        if Image.isImageUrl(imageId):
            raise Exceptions.ValidationException('Image ID was expected. Given %s' % imageId)
        if not self.downloader:
            self._createDownloader()
        return self.downloader.getImageElementValue('format', imageId)
            
    def _checkImageByUrl(self, imageUrl):
        try:
            Util.checkUrlExists(imageUrl)
        except (Exceptions.ValidationException, Exceptions.ExecutionException), ex:
            raise Exceptions.ValidationException("Unable to access image '%s': %s" %
                                      (imageUrl, str(ex)))
        else:
            self.printDetail('Image available: %s' % imageUrl)

    def _checkImageByIdInMarketplace(self, imageId):
        self._createDownloader()
        imageLocations = self._getImageLocationsByImageId(imageId)
        if not imageLocations:
            raise Exceptions.ValidationException('Image location(s) are not set in manifest for the image with ID %s' % imageId)
        else:
            self.printDetail('Manifest with ID %s is available. Image locations: %s' % 
                             (imageId, str(imageLocations)))

    def _getImageLocationsByImageId(self, imageId):
        """Return list of locations."""
        if not self.downloader:
            self._createDownloader()
        self.downloader.downloadManifestByImageId(imageId)
        return self.downloader.getImageLocations()

    def _createDownloader(self):
        if not self.downloader:
            configHolder = self.configHolder.copy()
            self.downloader = Downloader(configHolder)

    def printDetail(self, msg):
        return Util.printDetail(msg, self.verboseLevel, Util.DETAILED_VERBOSE_LEVEL)
