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
import re

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.HttpClient import HttpClient
from stratuslab.Exceptions import InputException
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab import Defaults
from stratuslab import Util
from Util import Util as MarketplaceUtil

class Uploader(object):

    def __init__(self, configHolder = ConfigHolder()):
        self.confHolder = configHolder
        configHolder.assign(self)

    @staticmethod
    def buildUploadParser(parser):
        parser.usage = '''usage: %prog [options] <metadata-file>'''

        MarketplaceUtil.addEndpointOption(parser)


    @staticmethod
    def checkUploadOptions(options, parser):
        MarketplaceUtil.checkEndpointOption(options)


    def upload(self, manifestFilename):
        client = HttpClient()
        if not os.path.exists(manifestFilename):
            raise InputException('Can\'t find metadata file: %s' % manifestFilename)
        
        manifest = open(manifestFilename).read()

        info = ManifestInfo(self.confHolder)
        info.parseManifest(manifest)
        
        url = MarketplaceUtil.metadataUrl(self.marketplaceEndpoint, info.identifier)
        client.post(url, manifest)

        finalUrl = MarketplaceUtil.metadataCompleteUrl(self.marketplaceEndpoint, 
                                                       info.identifier, 
                                                       info.email, 
                                                       info.created)
        print finalUrl
