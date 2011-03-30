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
import string
import time

import Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ExecutionException

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


NS_RDF     = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
NS_DCTERMS = 'http://purl.org/dc/terms/'
NS_SLTERMS = 'http://mp.stratuslab.eu/slterms#'
NS_SLREQ   = 'http://mp.stratuslab.eu/slreq#'

imageTypes = ['base', 'grid']
imageKinds = ('machine', 'disk')
imageFormats = ['raw', 'qcow2']

class ManifestInfo(object):

    NS_RDF     = NS_RDF
    NS_DCTERMS = NS_DCTERMS
    NS_SLTERMS = NS_SLTERMS
    NS_SLREQ   = NS_SLREQ

    IMAGE_VALIDITY = (356/2) * 24 * 3600 # 1/2 year in sec

    MANDATORY_CHECKSUMS = ('sha1',)
    CHECKSUM_NAMES = ('md5','sha1','sha256','sha512')

    def __init__(self, configHolder=ConfigHolder()):

        self.os = ''
        self.osversion = ''
        self.arch = ''
        self.type = '' # image type: base, grid, ..
        self.version = '' # image version

        self.created = '' # image creation time (in iso8601)
        self.user = self.creator = '' # full name of image creator

        self.compression = '' # image compression: gz, bz2, ..
        self.comment = ''
        self.filename = '' # filename of compressed image (old manifest)

        self.location = '' # URI of image in appliance repository

        self.kind = '' # image kind: machine, disk

        self.format = '' # image format: raw, qcow2, ..

        self.bytes = '0' # size of the uncompressed image on disk (in bytes)
        self.md5 = ''
        self.sha1 = ''
        self.sha256 = ''
        self.sha512 = ''

        self.valid = '' # ManifestInfo.created + ManifestInfo.IMAGE_VALIDITY (in iso8601)

        self.identifier = '' # base64 of int(sha1_hex, 16)
        self.serialnumber = ''
        self.hypervisor = '' # kvm, xen, ..

        self.publisher = 'StratusLab'

        configHolder.assign(self)

        self.user = self.creator

        self.template = os.path.join(Util.getShareDir(),'template/manifest.xml.tpl')

        self.attrsAndNamespaces = \
                            (('type','type',NS_DCTERMS,None),
                             ('created','created',NS_DCTERMS,None),
                             ('valid','valid',NS_DCTERMS,None),
                             ('os','os',NS_SLTERMS,None),
                             ('arch','os-arch',NS_SLTERMS,None),
                             ('osversion','os-version',NS_SLTERMS,None),
                             ('compression','compression',NS_DCTERMS,self.compression),
                             ('comment','description',NS_DCTERMS,None),
                             ('version','version',NS_SLTERMS,None))

    def parseManifest(self, manifest):
        xml = etree.fromstring(manifest)

        # skip endorsement element

        # required by Schema attributes
        for elem,ns in [('identifier',NS_DCTERMS), ('bytes',NS_SLREQ)]:
            try:
                val = getattr(xml.find('.//{%s}%s' % (ns, elem)), 'text')
            except AttributeError:
                raise ExecutionException("Missing mandatory element '%s' in namespace '%s'" %
                                         (elem, ns))
            else:
                attr = elem
                setattr(self, attr, val)

        checksums = xml.findall('.//{%s}checksum' % NS_SLREQ)
        for checksum in checksums:
            checkSumType = checksum.find('.//{%s}algorithm' % NS_SLREQ).text
            checkSumType = _normalizeForInstanceAttribute(checkSumType)
            checkSumValue = checksum.find('.//{%s}value' % NS_SLREQ).text
            setattr(self, checkSumType, checkSumValue)

        # attributes from integration XML template
        for attrObj,elemXml,ns,default in self.attrsAndNamespaces:
            try:
                attrVal = getattr(xml.find('.//{%s}%s' % (ns, elemXml)), 'text')
            except AttributeError:
                if default != None:
                    attrVal = default
                else:
                    raise ExecutionException("Missing element '%s' in namespace '%s'" % (elemXml, ns))
            else:
                setattr(self, attrObj, attrVal)

        # extra elements with defaults
        self.user = getattr(xml.find('.//{%s}creator' % NS_DCTERMS), 'text',
                            self.creator)
        self.creator = self.user
        self.kind = getattr(xml.find('.//{%s}kind' % NS_SLTERMS), 'text',
                            self.kind)
        self.format = getattr(xml.find('.//{%s}format' % NS_DCTERMS), 'text',
                                   self.format)
        self.hypervisor = getattr(xml.find('.//{%s}hypervisor' % NS_SLTERMS), 'text',
                                  self.hypervisor)
        self.location = getattr(xml.find('.//{%s}location' % NS_SLTERMS), 'text',
                                self.location)
        self.publisher = getattr(xml.find('.//{%s}publisher' % NS_DCTERMS), 'text',
                                 self.publisher)

    def parseManifestFromFile(self, filename):
        manifest = file(filename).read()
        self.parseManifest(manifest)

    def buildAndSave(self):
        manifestText = self.build()
        filename = '%s-%s-%s-%s-%s%s' % (self.os, self.osversion,
                                          self.arch, self.type,
                                          self.version, Util.manifestExt)
        file(filename, 'w').write(manifestText)
        Util.printDetail("Manifest: %s"%filename, verboseLevel=self.verboseLevel,
                         verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)

    def build(self):
        self.created = Util.getTimeInIso8601()
        self.valid = Util.toTimeInIso8601(time.time() + self.IMAGE_VALIDITY)
        identifier = ManifestIdentifier()
        self.identifier = identifier.sha1ToIdentifier(self.sha1)
        return self.tostring()

    def tostring(self):
        template = open(self.template).read()
        return template % self.__dict__

    def __str__(self):
        output = '* %s:\n' % self.__class__.__name__
        for k in self.__dict__:
            if not k.startswith('_') and not callable(k):
                output += '  %s = %s\n' % (k, self.__dict__[k])
        return output

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
        for _ in range(self.identifierChars):
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
