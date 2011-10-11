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
import tempfile
import urllib2

from Util import Util as MarketplaceUtil
from stratuslab.Exceptions import InputException, ExecutionException
from stratuslab.ManifestInfo import ManifestInfo
import stratuslab.Util as Util
from stratuslab import Defaults
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.ManifestInfo import _normalizeForInstanceAttribute as normalizeManifestElementForClassAttr

etree = Util.importETree()

class ManifestDownloader(object):

    ENDPOINT = Defaults.marketplaceEndpoint

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        self.manifestObject = None
        self.endpoint = ManifestDownloader.ENDPOINT
        configHolder.assign(self)

    def getManifestList(self, identifier):
        endpoint = Util.constructEndPoint(self.endpoint, 'http', '80', 'images')
        url = endpoint + '/' + identifier
        metadataEntries = ''
        try:
            metadataEntries = Util.wstring(url)
        except urllib2.HTTPError:
            raise InputException('Failed to find metadata entries: %s' % url)                

        return self._extractManifestInfos(self._parseXml(metadataEntries))
    
    def _parseXml(self, xmlAsString):
        return etree.fromstring(xmlAsString)

    def _extractManifestInfos(self, manifestRootElement):
        manifestElements = manifestRootElement.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
        manifests = []
        for e in manifestElements:
            manifest = ManifestInfo()
            manifest.parseManifestFromXml(e)
            manifests.append(manifest)
        return manifests        

    def getManifestInfo(self, resourceUri):
        tempFilename = tempfile.mktemp()
        try:
            return self._getManifest(resourceUri, tempFilename)
        finally:
            try:
                os.unlink(tempFilename)
            except:
                pass
            
    def getManifestAsFile(self, uri, filename):
        url = MarketplaceUtil.metadataUrl(self.marketplaceEndpoint, uri)
        self._downloadAsFile(url, filename)

    def getManifest(self, resourceUri):
        '''Return manifest as ManifestInfo object.
        '''
        return self._getManifest(resourceUri)

    def _getManifest(self, resourceUri):
        url = MarketplaceUtil.metadataUrl(self.marketplaceEndpoint, resourceUri)
        try:
            return self.__getManifest(url)
        except:
            print "Failed to get manifest for resource uri: %s" % resourceUri
            raise

    def __getManifest(self, url):
        errorMessage = 'Failed to find metadata entry: %s' % url
        try:
            manifest = self._download(url)
        except urllib2.HTTPError:
            raise InputException(errorMessage)
        
        if not manifest:
            raise InputException(errorMessage)

        manifestInfo = ManifestInfo(self.configHolder)
        
        try:
            manifestInfo.parseManifestFromXml(manifest)
        except ExecutionException, ex:
            raise InputException('Error parsing the metadata corresponding to url %s, with detail %s' % (url, ex))
        return manifestInfo

    def _download(self, url):
        xml = None
        try:
            xml = Util.wstring(url)
        except urllib2.URLError, ex:
            raise InputException('Failed to download: %s, with detail: %s' % (url, str(ex)))
        return self._parseXml(xml)

    def _downloadAsFile(self, url, filename):
        try:
            return Util.wget(url, filename)
        except urllib2.URLError, ex:
            raise InputException('Failed to download: %s, with detail: %s' % (url, str(ex)))

    def getImageLocations(self, imageId=''):
        return self.getImageElementValue('locations', imageId)

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
        self.manifestObject = self._getManifest(imageId)
