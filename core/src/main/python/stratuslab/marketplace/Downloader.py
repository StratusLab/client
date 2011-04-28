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
import urllib2
import hashlib
from stratuslab.ManifestInfo import _normalizeForInstanceAttribute as normalizeManifestElementForClassAttr

try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise Exception("Failed to import ElementTree from any known place")

from stratuslab import Util
from stratuslab.Exceptions import ExecutionException
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.Signator import Signator
from stratuslab.Compressor import Compressor
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import InputException
from stratuslab.Exceptions import ValidationException

class Downloader(object):

    ENDPOINT = 'http://appliances.stratuslab.eu/marketplace/metadata'
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

    def _getManifest(self, imageId, tempMetadataFilename):
        """Return manifest as ManifestInfo object.
        """
        url = self.constructManifestUrl(imageId)
        try:
            return self.__getManifest(url, tempMetadataFilename)
        except:
            print "Failed to get manifest for image: %s" % imageId
            raise

    def __getManifest(self, url, tempMetadataFilename):
        """Return manifest as ManifestInfo object.
        """
        errorMessage = 'Failed to find metadata entry: %s' % url
        try:
            self._download(url, tempMetadataFilename)
        except urllib2.HTTPError:
            raise InputException(errorMessage)
        
        if not os.path.exists(tempMetadataFilename):
            raise InputException(errorMessage)

        manifestInfo = ManifestInfo(self.configHolder)
        
        try:
            manifestInfo.parseManifestFromFile(tempMetadataFilename)
        except SyntaxError, ex:
            raise InputException('Error parsing the metadata corresponding to url %s, with detail %s' % (url, ex))
        return manifestInfo

    def getImageLocations(self, imageId=''):
        return [self.getImageElementValue('location', imageId)]

    def getImageVersion(self, imageId=''):
        return self.getImageElementValue('version', imageId)

    def getImageElementValue(self, element, imageId=''):
        if imageId:
            self._checkManifestAndImageId(imageId)
        elementNorm = normalizeManifestElementForClassAttr(element)
        try:
            return getattr(self.manifestObject, elementNorm)
        except AttributeError, ex:
            raise ExecutionException("Couldn't get '%s' element (normalized to '%s') from manifest. %s" % 
                                     (element, elementNorm, str(ex)))

    def _checkManifestAndImageId(self, imageId):
        if not self.manifestObject:
            self.downloadManifestByImageId(imageId)
        if imageId != self.manifestObject.identifier:
            raise InputException('Given image ID [%s] does not match to downloaded [%s]' % 
                                    (imageId, self.manifestObject.identifier))

    def downloadManifestByImageId(self, imageId):
        tempMetadataFilename = tempfile.mktemp()
        try:
            self.manifestObject = self._getManifest(imageId, tempMetadataFilename)
        finally:
            try:
                os.unlink(tempMetadataFilename)
            except:
                pass

    def download(self, uri):
        tempMetadataFilename = tempfile.mktemp()

        manifestInfo = self._getManifest(uri, tempMetadataFilename)

        locations = [manifestInfo.location]

        tempImageFilename = ''
        for location in locations:
            Util._printDetail('Looking for image: %s' % location)
            try:
                tempImageFilename = self._downloadImage(location)
                break
            except KeyboardInterrupt:
                raise
            except:
                pass

        if not os.path.exists(tempImageFilename):
            raise InputException('Failed to find image matching metadata: %s' % uri)

        self._verifySignature(tempImageFilename, tempMetadataFilename)

        tempImageFilename = self._inflateImage(tempImageFilename)

        self._verifyHash(tempImageFilename, manifestInfo.sha1)

        shutil.copy2(tempImageFilename, self.localImageFilename)

        os.remove(tempImageFilename)
        os.remove(tempMetadataFilename)

        return self.localImageFilename

    def constructManifestUrl(self, uri):
        endpoint = Util.constructEndPoint(self.marketplaceEndpoint, 'http', '80', 'images')
        url = endpoint + '/' + uri
        return url

    def _loadDom(self, filename):
        file = open(filename).read()
        dom = etree.fromstring(file)
        return dom

    def _downloadImage(self, url):
        compressionExtension = self._extractCompressionExtension(url)

        localFilename = tempfile.mktemp()
        localImageName = localFilename + compressionExtension

        Util.wget(url, localImageName)

        return localImageName

    def _extractCompressionExtension(self, url):
        compression = url.split('.')[-1]

        if compression in ('gz', 'bz2'):
            return '.' + compression
        else:
            return ''

    def _download(self, url, localFilename):
        try:
            return Util.wget(url, localFilename)
        except urllib2.URLError, ex:
            raise InputException('Failed to download: %s, with detail: %s' % (url, str(ex)))

    def _verifySignature(self, imageFilename, metadataFilename):
        signator = Signator(metadataFilename, self.configHolder)
        res = signator.validate()
        if res:
            raise ExecutionException('Failed to validate metadata file')

    def _inflateImage(self, imageFilename):
        extension = self._extractCompressionExtension(imageFilename)
        inflatedFilename = imageFilename
        if extension:
            Util._printDetail('Inflating image %s' % imageFilename)
            Compressor.inflate(imageFilename)
            inflatedFilename = imageFilename[:-len(extension)]

        return inflatedFilename

    def _verifyHash(self, imageFilename, hashFromManifest):

        data = open(imageFilename).read()
        sha1 = hashlib.sha1()
        sha1.update(data)

        imageHash = sha1.hexdigest()

        if imageHash != hashFromManifest:
            raise ValidationException('Manifest hash code different from downloaded image: image=%s, matadata=%s' % (imageHash, hashFromManifest))

    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, 1)

