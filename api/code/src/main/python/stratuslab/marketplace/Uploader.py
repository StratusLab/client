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

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.HttpClient import HttpClient
from stratuslab.Exceptions import InputException, ClientException,\
    ExecutionException
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.marketplace.Util import Util as MarketplaceUtil
from stratuslab.Util import importETree, etree_from_text

etree = importETree()

class Uploader(object):

    def __init__(self, configHolder = ConfigHolder()):
        self.confHolder = configHolder
        configHolder.assign(self)

    @staticmethod
    def buildUploadParser(parser):
        MarketplaceUtil.addEndpointOption(parser)


    @staticmethod
    def checkUploadOptions(options, parser):
        MarketplaceUtil.checkEndpointOption(options)


    def upload(self, manifestFilename):
        client = HttpClient(self.confHolder)
        if not os.path.exists(manifestFilename):
            raise InputException('Can\'t find metadata file: %s' % manifestFilename)

        manifest = open(manifestFilename).read()

        info = ManifestInfo(self.confHolder)
        info.parseManifest(manifest)

        url = MarketplaceUtil.metadataEndpointUrl(self.marketplaceEndpoint)
        try:
            client.post(url, manifest)
        except ClientException, ex:
            error = ''
            try:
                error = etree_from_text(ex.content).text
            except: pass
            raise ExecutionException("Failed to upload: %s: %s" % (ex.reason, error))
        except AttributeError, ex:
            raise ExecutionException("Failed to upload (post) to URL: %s" % url)

        finalUrl = MarketplaceUtil.metadataCompleteUrl(self.marketplaceEndpoint,
                                                       info.identifier,
                                                       info.email,
                                                       info.created)
        return finalUrl
