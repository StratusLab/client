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

import sys
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
        self.whiteListEndorsers = ['whiteListEndorsers']
        self.blackListEndorsers = ['blackListEndorsers']
        self.whiteListChecksums = ['whiteListChecksums']
        self.blackListChecksums = ['blackListChecksums']
        self.whiteListImages = ['whiteListImages']
        self.blackListImages = ['blackListImages']
        self.validateMetaData = []
        self.messageinfo = []
        self.intersectionList = ['whiteListImages','blackListImages','whiteListChecksums','blackListChecksums']
        self.policyConfigFilename = policyConfigFilename
        configHolder.assign(self)
        self._loadConfig(self.policyConfigFilename)

    def _loadConfig(self, configfile):
        if not os.path.exists(configfile):
            raise InputException("Can't find policy configuration file: %s" % configfile)
        config = ConfigParser.ConfigParser()
        config.read(configfile)
        sections=config.sections()
        if 'whitelistendorsers' in sections:
            for _,j in config.items('whitelistendorsers'):
                if j != '':
                    self.whiteListEndorsers.append(j)
        if 'blacklistendorsers' in sections:
            for _,j in config.items('blacklistendorsers'):
                if j != '':
                    self.blackListEndorsers.append(j)
        if 'blacklistchecksum' in sections:
            for _,j in config.items('blacklistchecksum'):
                if j != '':
                    self.blackListChecksums.append(j)
        if 'whitelistchecksum' in sections:
            for _,j in config.items('whitelistchecksum'):
                if j != '':
                    self.whiteListChecksums.append(j)
        if 'whitelistimages' in sections:
            for _,j in config.items('whitelistimages'):
                if j != '':
                    self.whiteListImages.append(j)
        if 'blacklistimages' in sections:
            for _,j in config.items('blacklistimages'):
                if j != '':
                    self.blackListImages.append(j)
        if 'validatemetadatafile' in sections:
            for _,j in config.items('validatemetadatafile'):
                if j != '':
                    self.validateMetaData.append(j)
    
    def check(self, identifierUri):
        if self._isActive():
            self._validate(identifierUri)
        self._loadDom(self._downloadManifest(identifierUri))

        metadatas = self._retrieveMetadataList()
        metadataEntries = metadatas.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')

        filterList = [self.whiteListImages,
                      self.blackListImages,
                      self.whiteListEndorsers,
                      self.blackListEndorsers,
                      self.whiteListChecksums,
                      self.blackListChecksums]
        
        remainingMetadataEntries = metadataEntries
        
        for list in filterList:
            remainingMetadataEntries = self._filter(remainingMetadataEntries, list)
            if len(remainingMetadataEntries) == 0:
                sys.stderr.write(self._errorMessage())
                raise ValidationException('Policy check Failed')
        
        return remainingMetadataEntries


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
        return self.manifest.findtext('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://purl.org/dc/terms/}identifier')
        
    #filter: inputs: metadata list as element tree.
    #     remove unwanted element tree from metadata list
    #     return metadata list  
    
    def _filter(self, metadatas, whiteOrBlackList):
        metadata_to_remove=[]
        if whiteOrBlackList[0] in self.intersectionList:
            if not self._keep(metadatas[0], whiteOrBlackList):
                metadata_to_remove.extend(metadatas)
        else:
            for metadata in metadatas:
                if not self._keep(metadata, whiteOrBlackList):
                    metadata_to_remove.append(metadata)
        for metadata in metadata_to_remove:
            metadatas.remove(metadata)
        return metadatas

    # keep: inputs: element tree
    #	retrieve email endorser and checksum value from the elemet tree
    #	return true email endorser listed in WhiteListEndorsers and checksum value is not listed in BlackListChecksums

    def _keep(self, metadata, whiteOrblackList):
        xpathPrefix = './/{http://mp.stratuslab.eu/slreq#}%s/{http://mp.stratuslab.eu/slreq#}'

        # TODO: refactor this using the ManifestInfo class
        emailendorser = metadata.findtext(xpathPrefix % 'endorser' + 'email')
        imageidentifier = metadata.findtext('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://purl.org/dc/terms/}identifier')
        checksumimages = metadata.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://mp.stratuslab.eu/slreq#}checksum')

        if (whiteOrblackList[0] == 'whiteListImages' and len(self.whiteListImages)>1):
            return self._whiteListImagesPlugin(imageidentifier)
        elif (whiteOrblackList[0] == 'blackListImages' and len(self.blackListImages)>1):
            return self._blackListImagesPlugin(imageidentifier)
        elif (whiteOrblackList[0] == 'whiteListEndorsers' and len(self.whiteListEndorsers)>1):
            return self._whiteListEndorsersPlugin(emailendorser)
        elif (whiteOrblackList[0] == 'blackListEndorsers' and len(self.blackListEndorsers)>1):
            return self._blackListEndorsersPlugin(emailendorser)
        elif (whiteOrblackList[0] == 'whiteListChecksums' and len(self.whiteListChecksums)>1):
            return self._whiteListChecksumsPlugin(checksumimages)
        elif (whiteOrblackList[0] == 'blackListChecksums' and len(self.blackListChecksums)>1):
            return self._blackListChecksumsPlugin(checksumimages)
        else:
            print"Warning : no policy %s defined" % whiteOrblackList[0]
            return True      

    def _whiteListEndorsersPlugin(self, emailendorser):
        if (emailendorser in self.whiteListEndorsers):
            print "email endorser %s is  whitelisted" %emailendorser
            return True
        else:
            self.messageinfo.append("email endorser %s is not whitelisted" %emailendorser)
            return False

    def _blackListEndorsersPlugin(self, emailendorser):
        if (emailendorser not in self.blackListEndorsers):
            print "email endorser %s is not blacklisted" %emailendorser
            return True
        else:
            self.messageinfo.append("email endorser %s is blacklisted" %emailendorser)
            return False
    

    def _whiteListChecksumsPlugin(self, checksumimages):
        for checksumimage in checksumimages:
            if (checksumimage.findtext('{http://mp.stratuslab.eu/slreq#}algorithm') == 'SHA-1'):
                checksum_sha1 = checksumimage.findtext('{http://mp.stratuslab.eu/slreq#}value')
        if (checksum_sha1  in self.whiteListChecksums):
            print "SHA-1 checksum image %s is whitelisted" %checksum_sha1
            return True
        else:
            self.messageinfo.append("SHA-1 checksum image %s is not whitelisted" %checksum_sha1)
            return False

    def _blackListChecksumsPlugin(self, checksumimages):
        for checksumimage in checksumimages:
            if (checksumimage.findtext('{http://mp.stratuslab.eu/slreq#}algorithm') == 'SHA-1'):
                checksum_sha1 = checksumimage.findtext('{http://mp.stratuslab.eu/slreq#}value')
        if (checksum_sha1 not in self.blackListChecksums):
            print "SHA-1 checksum image %s is not blacklisted" %checksum_sha1
            return True
        else:
            self.messageinfo.append("SHA-1 checksum image %s is blacklisted" %checksum_sha1)
            return False

    def _whiteListImagesPlugin(self, imageidentifier):
        if imageidentifier in self.whiteListImages:
            print "image identifier %s is whitelisted" %imageidentifier
            return True
        else:
            self.messageinfo.append("image identifier %s is not whitelisted" %imageidentifier)
            return False

    def _blackListImagesPlugin(self, imageidentifier):
        if imageidentifier not in self.blackListImages:
            print "image identifier %s is not blacklisted" %imageidentifier
            return True
        else:
            self.messageinfo.append("image identifier %s is blacklisted" %imageidentifier)
            return False

    def _isActive(self):
        return (Util.isTrueConfVal(self.validateMetaData[0]) and True) or False

    def _validate(self, identifierUri):
        configHolder = ConfigHolder()
        configHolder.set('verboseLevel', 3)
        downloader = Downloader(configHolder)
        downloader.download(identifierUri)
        



    def _errorMessage(self):
        self.messageinfo.append("Image isn't valid according to site policy\n")
        return '\n'.join(self.messageinfo)



