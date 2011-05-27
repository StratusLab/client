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
import ConfigParser
import urllib2
from stratuslab import Defaults

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

import stratuslab.Util as Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ValidationException, InputException
from stratuslab.marketplace.Downloader import Downloader

class Policy(object):

    POLICY_CFG = os.path.join(Defaults.ETC_DIR, 'policy.cfg')

    def __init__(self, policyConfigFilename, configHolder = ConfigHolder()):
        self.whiteListEndorsers = ['whiteListEndorsersFlag']
        self.blackListChecksums = ['blackListChecksumsFlag']
        self.whiteListImages = ['whiteListImagesFlag']
        self.blackListImages = ['blackListImagesFlag']
        self.validateMetaData = []
        self.policyConfigFilename = policyConfigFilename
        configHolder.assign(self)
        self._loadConfig(self.policyConfigFilename)

    def _loadConfig(self, configfile):
        if not os.path.exists(configfile):
            raise InputException("Can't find policy configuration file: %s" % configfile)
        config = ConfigParser.ConfigParser()
        config.read(configfile)
        for _,j in config.items('whitelistendorsers'):
            self.whiteListEndorsers.append(j)
        for _,j in config.items('blacklistchecksums'):
            self.blackListChecksums.append(j)
        for _,j in config.items('validatemetadatafile'):
            self.validateMetaData.append(j)
        for _,j in config.items('whitelistimages'):
            self.whiteListImages.append(j)	    
        for _,j in config.items('blacklistimages'):
            self.blackListImages.append(j)    
    
    def check(self, identifierUri):
        if self._isActive():
            print "validation process"
            self._validate(identifierUri)
        self._loadDom(self._downloadManifest(identifierUri))

        metadatas = self._retrieveMetadataList()
        #metadataEntries = metadatas.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
        metadataEntries=[metadatas]
        filtered0 = self._filter(metadataEntries, self.whiteListImages)
        if len(filtered0) == 0:
            raise ValidationException('Failed policy check')
        print len(filtered0)

        filtered1 = self._filter(filtered0, self.blackListImages)
        if len(filtered1) == 0:
            raise ValidationException('Failed policy check')
        print len(filtered1)

        filtered2 = self._filter(filtered1, self.whiteListEndorsers)
        if len(filtered2) == 0:
            raise ValidationException('Failed policy check')
        print len(filtered2)
        
        filtered3 = self._filter(filtered2, self.blackListChecksums)	
        if len(filtered3) == 0:
            raise ValidationException('Failed policy check')
        print len(filtered3)

    def _downloadManifest(self, identifierUri):
        endpoint = Util.constructEndPoint(self.endpoint, 'http', '80', 'images')
        url = endpoint + '/' + identifierUri
        try:
            manifest = Util.wstring(url)
        except urllib2.HTTPError:
            raise InputException('Failed to find metadata entry: %s' % url)                
        return manifest

    def _loadDom(self, xml):
        self.manifest = etree.fromstring(xml)

    def _retrieveMetadataList(self):
        identifier = self._extractIdentifier()
        endpoint = Util.constructEndPoint(self.endpoint, 'http', '80', 'images')
        url = endpoint + '/' + identifier
        metadataEntries = ''
        try:
            metadataEntries = Util.wstring(url)
        except urllib2.HTTPError:
            raise InputException('Failed to find metadata entries: %s' % url)                

        return etree.fromstring(metadataEntries)

    def _extractIdentifier(self):
        return self.manifest.findtext('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://purl.org/dc/terms/}identifier')
        
    #filter: inputs: metadata list as element tree.
    #     remove unwanted element tree from metadata list
    #     return metadata list  
    
    def _filter(self, metadatas, whiteOrblackList):
        for metadata in metadatas:
            if not self._keep(metadata, whiteOrblackList):
                metadatas.remove(metadata)
                print 'removing...'
        return metadatas

    # keep: inputs: element tree
    #	retrieve email endorser and checksum value from the elemet tree
    #	return true email endorser listed in WhiteListEndorsers and checksum value is not listed in BlackListChecksums

    def _keep(self, metadata, whiteOrblackList):
        xpathPrefix = './/{http://mp.stratuslab.eu/slreq#}%s/{http://mp.stratuslab.eu/slreq#}'
        emailendorser = metadata.findtext(xpathPrefix % 'endorser' + 'email')
        imageidentifier = metadata.findtext('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://purl.org/dc/terms/}identifier')
        checksumimages = metadata.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://mp.stratuslab.eu/slreq#}checksum')
        
        if (whiteOrblackList[0] == 'whiteListImagesFlag'):
            return self._whiteListImagesPlugin(imageidentifier)
        elif (whiteOrblackList[0] == 'blackListImagesFlag'):
            return self._blackListImagesPlugin(imageidentifier)
        elif (whiteOrblackList[0] == 'whiteListEndorsersFlag'):
            return self._whiteListEndorsersPlugin(emailendorser)
        elif (whiteOrblackList[0] == 'blackListChecksumsFlag'):
            return self._blackListChecksumsPlugin(checksumimages)

    def _whiteListEndorsersPlugin(self, emailendorser):
        if (emailendorser in self.whiteListEndorsers):
            print True
            return True
        else:
            print False
            return False

    def _blackListChecksumsPlugin(self, checksumimages):
        for checksumimage in checksumimages:
            if (checksumimage.findtext('{http://mp.stratuslab.eu/slreq#}algorithm') == 'SHA-1'):
                checksum_sha1 = checksumimage.findtext('{http://mp.stratuslab.eu/slreq#}value')
        if (checksum_sha1 not in self.blackListChecksums):
            print True
            return True
        else:
            print False
            return False

    def _whiteListImagesPlugin(self, imageidentifier):
        if (imageidentifier in self.whiteListImages):
            print True
            return True
        else:
            print False
            return False

    def _blackListImagesPlugin(self, imageidentifier):
        if (imageidentifier not in self.blackListImages):
            print True
            return True
        else:
            print False
            return False

    def _isActive(self):
        return (Util.isTrueConfVal(self.validateMetaData[0]) and True) or False

    def _validate(self, identifierUri):
        configHolder = ConfigHolder()
        configHolder.set('verboseLevel', 3)
        downloader = Downloader(configHolder)
        downloader.download(identifierUri)
        
