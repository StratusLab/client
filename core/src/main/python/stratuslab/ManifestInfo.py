#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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
import string

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

import Util

NS_RDF     = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
NS_DCTERMS = 'http://purl.org/dc/terms/'
NS_SLTERMS = 'http://stratuslab.eu/terms#'
NS_SLREQ   = 'http://mp.stratuslab.eu/slreq#'

class ManifestInfo(object):

    NS_RDF     = NS_RDF
    NS_DCTERMS = NS_DCTERMS
    NS_SLTERMS = NS_SLTERMS
    NS_SLREQ   = NS_SLREQ

    def __init__(self, ):
        self.created = ''
        self.type = ''
        self.version = ''
        self.os = ''
        self.arch = ''
        self.user = ''
        self.os = ''
        self.osversion = ''
        self.compression = ''
        self.comment = ''
        self.filename = ''

        self.bytes = '0'
        self.md5 = ''
        self.sha1 = ''
        self.sha256 = ''
        self.sha512 = ''

        self.valid = ''

        self.identifier = ''
        self.serialnumber = ''
        self.hypervisor = ''

        self.publisher = 'StratusLab'

        self.template = os.path.join(Util.getShareDir(),'template/manifest.xml.tpl')

    def parseManifest(self, manifest):
        xml = etree.fromstring(manifest)
        if xml.tag == 'manifest':
            self.os = xml.find('os').text
            self.osversion = xml.find('osversion').text
            self.arch = xml.find('arch').text
            self.type = xml.find('type').text
            self.version = xml.find('version').text
            self.compression = xml.find('compression').text
            self.user = xml.find('user').text
            self.created = xml.find('created').text
            self.filename = xml.find('filename').text
            checksums = xml.findall('checksum')
            for checksum in checksums:
                setattr(self, checksum.attrib['type'], checksum.text)
        else:
            self.title = xml.find('.//{%s}title' % NS_DCTERMS).text
            self.type = xml.find('.//{%s}type' % NS_DCTERMS).text
            self.created = xml.find('.//{%s}created' % NS_DCTERMS).text
            self.user = getattr(xml.find('.//{%s}creator' % NS_DCTERMS), 'text', '')
            self.valid = xml.find('.//{%s}valid' % NS_DCTERMS).text
            self.publisher = getattr(xml.find('.//{%s}publisher' % NS_DCTERMS), 'text',
                                     self.publisher) or self.publisher
            self.version = xml.find('.//{%s}version' % NS_SLTERMS).text
            self.serialnumber = xml.find('.//{%s}serial-number' % NS_SLTERMS).text
            self.arch = xml.find('.//{%s}os-arch' % NS_SLTERMS).text
            self.os = xml.find('.//{%s}os' % NS_SLTERMS).text
            self.osversion = xml.find('.//{%s}os-version' % NS_SLTERMS).text
            self.hypervisor = xml.find('.//{%s}hypervisor' % NS_SLTERMS).text
            self.filename = xml.find('.//{%s}title' % NS_DCTERMS).text
            self.compression = getattr(xml.find('.//{%s}format' % NS_DCTERMS), 'text',
                                       self.compression)
            self.identifier = xml.find('.//{%s}identifier' % NS_DCTERMS).text
            self.bytes = xml.find('.//{%s}bytes' % NS_SLREQ).text
            checksums = xml.findall('.//{%s}checksum' % NS_SLREQ)
            for checksum in checksums:
                checkSumType = checksum.find('.//{%s}algorithm' % NS_SLREQ).text
                checkSumType = _normalizeForInstanceAttribute(checkSumType)
                checkSumValue = checksum.find('.//{%s}value' % NS_SLREQ).text
                setattr(self, checkSumType, checkSumValue)
            self.comment = xml.find('.//{%s}description' % NS_DCTERMS).text

    def parseManifestFromFile(self, filename):
        manifest = file(filename).read()
        self.parseManifest(manifest)

    def tostring(self):
        template = open(self.template).read()
        return template % self.__dict__

class ManifestIdentifier(object):
    encoding = string.ascii_uppercase + string.ascii_lowercase + string.digits + '-_'
    encoding = [x for x in encoding]

    decoding = {}
    for i,v in enumerate(encoding):
        decoding[v] = long(i)

    sha1Bits = 160
    fieldBits = 6
    identifierChars = sha1Bits / fieldBits + 1
    devisor = long(2) ** fieldBits

    def sha1ToIdentifier(self, sha1):
        sha1 = int(sha1, 16)
        sb = ''
        for i in range(self.identifierChars):
            values = divmod(sha1, self.devisor)
            sha1 = values[0]
            sb += self.encoding[int(values[1])]
        return sb[::-1]


    def identifierToSha1(self, identifier):
        sha1 = long(0)
        for i in range(len(identifier)):
            sha1 = sha1 << self.fieldBits
            bits = long(self.decoding[identifier[i:i+1]])
            sha1 = sha1 | bits
        return hex(sha1).lstrip('0x').rstrip('L')

def _normalizeForInstanceAttribute(attr):
    return _removeDashes(attr.lower())

def _removeDashes(string):
    return re.sub('-', '', string)
