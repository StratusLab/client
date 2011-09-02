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
import copy

from stratuslab import Util
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.Signator import Signator
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.AuthnCommand import P12Certificate

from stratuslab.marketplace.Uploader import Uploader
from stratuslab.marketplace.Downloader import Downloader

from Util import Util as MarketplaceUtil

class Deprecator(object):

    @staticmethod
    def buildDeprecatorParser(parser):
        parser.usage = '''usage: %prog [options] <image id>'''

        MarketplaceUtil.addEndpointOption(parser)
        P12Certificate.addOptions(parser)

        parser.add_option('--email', dest='email',
                help='email address if not in certificate',
                default='')

        parser.add_option('--reason', dest='reason',
                help='Comment to append to deprecation',
                default='This image has been deprecated', metavar='TEXT')

    @staticmethod
    def checkDeprecatorOptions(options, parser):
        MarketplaceUtil.checkEndpointOption(options)

        if not P12Certificate.checkOptions(options):
            self.parser.error('Missing credentials. Please provide %s' % P12Certificate.optionString)

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        self.deprecated_xml = '<slterms:deprecated>%(reason)s</slterms:deprecated>'

        configHolder.assign(self)

        self.manifestObject = None
        self.uploader = Uploader(configHolder)
        self.downloader = Downloader(configHolder)

    def deprecate(self, imageId):
        tempMetadataFilename = tempfile.mktemp()
        tempDeprecatedMetadataFilename = tempfile.mktemp()
        try:
            self.manifestObject = self.downloader._getManifest(imageId, tempMetadataFilename)
            self.manifestObject.__dict__.update({'deprecated':self._getDeprecatedAsXml()})
            manifestText = self.manifestObject.build()
            file(tempDeprecatedMetadataFilename, 'w').write(manifestText)
            signator = Signator(tempDeprecatedMetadataFilename, self.configHolder)
            isError = signator.sign()
            self.uploader.upload(tempDeprecatedMetadataFilename)
        finally:
            try:
                os.unlink(tempMetadataFilename)
                os.unlink(tempDeprecatedMetadataFilename)
                os.unlink(tempDeprecatedMetadataFilename+'.orig')
            except:
                pass

    def _getDeprecatedAsXml(self):
        joint = '\n        '
        return joint.join([copy.copy(self.deprecated_xml) % {'reason':self.reason}])
