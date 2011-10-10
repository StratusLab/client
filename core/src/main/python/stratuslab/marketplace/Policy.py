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

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ValidationException, InputException
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader

class Filter(object):
    
    def __init__(self, messages):
        self.filterItems = []
        self.messages = messages
        self.successMessage = None
        self.failedMessage = None

    def _loadConfig(self, sectionName, configParameterName):
        configFile = Policy.POLICY_CFG
        if not os.path.exists(configFile):
            raise InputException("Can't find policy configuration file: %s" % configFile)
        config = ConfigParser.ConfigParser()
        config.read(configFile)
        try:
            rawFilterItems = config.get(sectionName, configParameterName)
            self.filterItems = filter(None,[item.strip() for item in rawFilterItems.split('\n')])
        except ConfigParser.NoOptionError:
            pass

    def filter(self, metadatas):

        for metadata in metadatas:
            candidate = self._getCandidate(metadata)
            if self._filterSingle(candidate) is False:
                metadatas.remove(metadata)

        return metadatas

    def _getCandidate(self, manifestInfo):
        pass
    
    def _filterSingle(self, candidate):
        pass
    

class BlackListBaseFilter(Filter):

    def _filterSingle(self, candidate):
        if candidate not in self.filterItems:
            self.messages.append(self.successMessage % candidate)
            return True
        else:
            self.messages.append(self.failedMessage % candidate)
            return False

class WhiteListBaseFilter(Filter):

    def _filterSingle(self, candidate):
        if candidate in self.filterItems:
            self.messages.append(self.successMessage % candidate)
            return True
        else:
            self.messages.append(self.failedMessage % candidate)
            return False

class WhiteListEndorsersFilter(WhiteListBaseFilter):
    
    def __init__(self, messages):
        super(WhiteListEndorsersFilter, self).__init__(messages)
        self._loadConfig('endorsers', 'whitelistendorsers')
        self.successMessage = 'email endorser %s is whitelisted, keeping entry'
        self.failedMessage = 'email endorser %s is not whitelisted, removing corresponding entry'

    def _getCandidate(self, manifestInfo):
        return manifestInfo.endorser


class BlackListEndorsersFilter(BlackListBaseFilter):
    
    def __init__(self, messages):
        super(BlackListEndorsersFilter, self).__init__(messages)
        self._loadConfig('endorsers', 'blacklistendorsers')
        self.successMessage = 'email endorser %s is not blacklisted, keeping entry'
        self.failedMessage = 'email endorser %s is blacklisted, removing corresponding entry'

    def _getCandidate(self, manifestInfo):
        return manifestInfo.endorser


class WhiteListChecksumsFilter(WhiteListBaseFilter):
    
    def __init__(self, messages):
        super(WhiteListChecksumsFilter, self).__init__(messages)
        self._loadConfig('checksums', 'whitelistchecksums')
        self.successMessage = 'SHA-1 checksum image %s is whitelisted, keeping entry'
        self.failedMessage = 'SHA-1 checksum image %s is not whitelisted, removing corresponding entry'

    def _getCandidate(self, manifestInfo):
        return manifestInfo.sha1


class BlackListChecksumsFilter(BlackListBaseFilter):
    
    def __init__(self, messages):
        super(BlackListChecksumsFilter, self).__init__(messages)
        self._loadConfig('checksums', 'blacklistchecksums')
        self.successMessage = 'SHA-1 checksum image %s is not blacklisted, keeping entry'
        self.failedMessage = 'SHA-1 checksum image %s is blacklisted, removing corresponding entry'

    def _getCandidate(self, manifestInfo):
        return manifestInfo.sha1


class WhiteListImagesFilter(WhiteListBaseFilter):
    
    def __init__(self, messages):
        super(WhiteListImagesFilter, self).__init__(messages)
        self._loadConfig('images', 'whitelistimages')
        self.successMessage = 'image identifier %s is whitelisted, keeping entry'
        self.failedMessage = 'image identifier %s is not whitelisted, removing corresponding entry'

    def _getCandidate(self, manifestInfo):
        return manifestInfo.identifier


class BlackListImagesFilter(BlackListBaseFilter):
    
    def __init__(self, messages):
        super(BlackListImagesFilter, self).__init__(messages)
        self._loadConfig('images', 'blacklistimages')
        self.successMessage = 'image identifier %s is not blacklisted, keeping entry'
        self.failedMessage = 'image identifier %s is blacklisted, removing corresponding entry'

    def _getCandidate(self, manifestInfo):
        return manifestInfo.identifier


class Policy(object):

    POLICY_CFG = os.path.join(Defaults.ETC_DIR, 'policy.cfg')

    def __init__(self, configHolder = ConfigHolder()):
        self.messages = []
        configHolder.assign(self)
        self.filters = self._loadFilters()

    def _loadFilters(self):
        filters = []

        whiteListEndorsersFilter = WhiteListEndorsersFilter(self.messages)
        if whiteListEndorsersFilter.filterItems:
            filters.append(whiteListEndorsersFilter)

        blackListEndorsersFilter = BlackListEndorsersFilter(self.messages)
        if blackListEndorsersFilter.filterItems:
            filters.append(blackListEndorsersFilter)

        whiteListChecksumsFilter = WhiteListChecksumsFilter(self.messages)
        if whiteListChecksumsFilter.filterItems:
            filters.append(whiteListChecksumsFilter)

        blackListChecksumsFilter = BlackListChecksumsFilter(self.messages)
        if blackListChecksumsFilter.filterItems:
            filters.append(blackListChecksumsFilter)

        whiteListImagesFilter = WhiteListImagesFilter(self.messages)
        if whiteListImagesFilter.filterItems:
            filters.append(whiteListImagesFilter)

        blackListImagesFilter = BlackListImagesFilter(self.messages)
        if blackListImagesFilter.filterItems:
            filters.append(blackListImagesFilter)

        return filters

    def check(self, identifierUri):

        manifests = self._downloadManifests(identifierUri)

        remainingMetadataEntries = manifests
        
        for filter in self.filters:
            remainingMetadataEntries = filter.filter(remainingMetadataEntries)

        if len(remainingMetadataEntries) == 0:
            sys.stderr.write(self._errorMessage())
            raise ValidationException('Policy check Failed')
        
        return remainingMetadataEntries

    def _downloadManifests(self, identifier):
        return ManifestDownloader().getManifestList(identifier)

    def _errorMessage(self):
        self.messages.append("Image isn't valid according to site policy\n")
        return '\n'.join(self.messages)



