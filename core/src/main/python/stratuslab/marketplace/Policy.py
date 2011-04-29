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

    def __init__(self, policyConfigFilename, configHolder = ConfigHolder()):
        self.whiteListEndorsers = ['whiteListEndorsersFlag']
        self.blackListChecksums = ['blackListChecksumsFlag']
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
    
    def check(self, identifierUri):
	if not self._deactivateMetadataValidation():
	    print "validation processus"
      	    self._Validate(identifierUri)
        self._loadDom(self._downloadManifest(identifierUri))

        metadatas = self._retrieveMetadataList()
        #metadataEntries = metadatas.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
	metadataEntries=[metadatas]
        filtered1 = self._filter(metadataEntries, self.whiteListEndorsers)
        filtered2 = self._filter(filtered1, self.blackListChecksums)	
        if len(filtered2) == 0:
            raise ValidationException('Failed policy check')
        print len(filtered2)

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
        checksumimage = metadata.findtext(xpathPrefix % 'checksum' + 'value')
        if (whiteOrblackList[0] == 'whiteListEndorsersFlag'):
            return self._whiteListEndorsersPlugin(emailendorser)
        elif (whiteOrblackList[0] == 'blackListChecksumsFlag'):
            return self._blackListChecksumsPlugin(checksumimage)

    def _whiteListEndorsersPlugin(self, emailendorser):
        if (emailendorser in self.whiteListEndorsers):
            print True
            return True
        else:
            print False
            return False

    def _blackListChecksumsPlugin(self, checksumimage):
        if (checksumimage not in self.blackListChecksums):
            print True
            return True
        else:
            print False
            return False

    def _deactivateMetadataValidation(self):
	if (self.validateMetaData[0] == 'no'):
            return True
	else:
	    return False
	
    def _Validate(self, identifierUri):
        configHolder = ConfigHolder()
        configHolder.set('verboseLevel', 3)
        downloader = Downloader(configHolder)
	downloader.download(identifierUri)
			
