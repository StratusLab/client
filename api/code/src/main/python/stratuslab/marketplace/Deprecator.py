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

from stratuslab import Util
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.Signator import Signator
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.AuthnCommand import P12Certificate

from stratuslab.marketplace.Uploader import Uploader

from Util import Util as MarketplaceUtil
from stratuslab.Exceptions import ExecutionException
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader

etree = Util.importETree()

class Deprecator(object):

    @staticmethod
    def buildDeprecatorParser(parser):
        parser.usage = '''usage: %prog [options] image-id'''

        parser.description = '''
Create a new metadata entry for the given image that deprecates the
image.  The reason for the deprecation must be given. The image-id
argument is the identifier of the image to deprecate.
'''

        MarketplaceUtil.addEndpointOption(parser)
        P12Certificate.addOptions(parser)

        parser.add_option('--email', dest='email',
                help='email address of endorser of metadata entry',
                default='')

        parser.add_option('--created', dest='created',
                help='date of metadata entry to be deprecated, latest entry will be deprecated if not provided',
                default='')

        parser.add_option('--reason', dest='reason',
                help='Comment to append to deprecation',
                default='This image has been deprecated', metavar='TEXT')

    @staticmethod
    def checkDeprecatorOptions(options, parser):
        MarketplaceUtil.checkEndpointOption(options)

        if not P12Certificate.checkOptions(options):
            parser.error('Missing credentials. Please provide %s' % P12Certificate.optionString)

        if not options.email:
            parser.error('Missing email address. Please provide email of endorser')

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder

        configHolder.assign(self)

        self.uploader = Uploader(configHolder)
        self.manifestDownloader = ManifestDownloader(configHolder)

    def deprecate(self, imageId):
        tempDeprecatedMetadataFilename = tempfile.mktemp()
        tempMetadataFilename = tempfile.mktemp()
        try:
            imageURI = imageId + '/' + self.email
            if len(self.created) != 0:
                imageURI = imageURI + '/' + self.created

            # Get metadata file
            self.manifestDownloader.getManifestAsFile(imageURI, tempMetadataFilename)

            # Strip signature
            xml = etree.ElementTree(file=tempMetadataFilename)
            root = xml.getroot()

            if (root.tag == "metadata"):
                rootElement = root.find('.//{%s}RDF' % ManifestInfo.NS_RDF)
            else:
                rootElement = root

            descriptionElement = rootElement.find('.//{%s}Description' % ManifestInfo.NS_RDF)
            descriptionElement.remove(descriptionElement.find('.//{%s}endorsement' % ManifestInfo.NS_SLREQ))
            endorsement = etree.Element('{%s}%s' % (ManifestInfo.NS_SLREQ, 'endorsement'), parseType="Resource")
            descriptionElement.append(endorsement)

            signatureElement = rootElement.find('.//{%s}Signature' % 'http://www.w3.org/2000/09/xmldsig#')
            rootElement.remove(signatureElement)

            xml._setroot(rootElement)

            # Add deprecated entry
            elem = etree.Element('{%s}%s' % (ManifestInfo.NS_SLTERMS, 'deprecated'))
            elem.text = self.reason
            descriptionElement.append(elem)

            xml.write(tempDeprecatedMetadataFilename)

            # Sign and upload
            signator = Signator(tempDeprecatedMetadataFilename, self.configHolder)

            isError = signator.sign()
            if isError:
                raise ExecutionException('Error signing new manifest')
            
            return self.uploader.upload(tempDeprecatedMetadataFilename)
        finally:
            try:
                os.unlink(tempMetadataFilename)
                os.unlink(tempDeprecatedMetadataFilename)
                os.unlink(tempDeprecatedMetadataFilename+'.orig')
            except:
                pass
