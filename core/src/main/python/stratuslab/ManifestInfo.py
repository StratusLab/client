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
import copy

import stratuslab.Util as Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ExecutionException

etree = Util.importETree()

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

        self.email = '' # email address of endorser

        self.compression = '' # image compression: gz, bz2, ..
        self.comment = ''
        self.filename = '' # filename of compressed image (old manifest)

        self.deprecated = ''

        self.locations = [] # list of image URIs
        self._locations_xml = '<slterms:location>%(location)s</slterms:location>'

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

        self._template = os.path.join(os.path.join(Util.getTemplateDir(), 'manifest.xml.tpl'))

        self._attrsAndNamespaces = \
                            (('type','type',NS_DCTERMS,None),
                             ('created','created',NS_DCTERMS,None),
                             ('valid','valid',NS_DCTERMS,None),
                             ('os','os',NS_SLTERMS,None),
                             ('arch','os-arch',NS_SLTERMS,None),
                             ('osversion','os-version',NS_SLTERMS,None),
                             ('compression','compression',NS_SLTERMS,self.compression),
                             ('comment','description',NS_DCTERMS,None),
                             ('version','version',NS_SLTERMS,None))

    @staticmethod
    def addElementToManifest(root, elementName, value):
        elems = root.findall('.//{%s}%s' % (ManifestInfo.NS_SLTERMS, elementName))

        if elems:
            # Check if already present. If yes, do nothing.
            for elem in elems:
                if elem.text and elem.text == value:
                    Util.printWarning("Element '%s' with value '%s' already defined in the manifest. Skipping addition of the element." % \
                                      (elementName, elem.text))
                    return

        elem = etree.Element('{%s}%s' % (ManifestInfo.NS_SLTERMS, elementName))
        elem.text = value

        descriptionElement = root.find('.//{%s}Description' % ManifestInfo.NS_RDF)
        descriptionElement.append(elem)

    @staticmethod
    def addElementToManifestFile(manifestfile, elementName, value):
        """TODO: check if given element is a valid one according to schema."""
        root = etree.ElementTree(file=manifestfile)

        ManifestInfo.addElementToManifest(root, elementName, value)

        root.write(manifestfile)

    def parseManifest(self, manifest):

        try:
            xml = etree.fromstring(manifest)
        except SyntaxError, ex:
            raise ExecutionException('Unable to parse manifest: %s\nMANIFEST:\n%s' % 
                                     (str(ex), manifest))
        
        return self.parseManifestFromXml(xml)

    def parseManifestFromXml(self, xml):

        xpathPrefix = './/{http://mp.stratuslab.eu/slreq#}%s/{http://mp.stratuslab.eu/slreq#}'
        self.endorser = xml.findtext(xpathPrefix % 'endorser' + 'email')

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
        for attrObj,elemXml,ns,default in self._attrsAndNamespaces:
            try:
                attrVal = getattr(xml.find('.//{%s}%s' % (ns, elemXml)), 'text')
            except AttributeError:
                if default != None:
                    attrVal = default
                else:
                    raise ExecutionException("Missing element '%s' in namespace '%s'" % (elemXml, ns))
            else:
                setattr(self, attrObj, attrVal)

        # email and endorsement timestamp if present
        self.email = getattr(xml.find('.//{%s}email' % NS_SLREQ), 'text',
                            self.email)
        self.created = getattr(xml.find('.//{%s}endorsement/{%s}created' % (NS_SLREQ, NS_DCTERMS)), 'text',
                            self.created)

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
        self.publisher = getattr(xml.find('.//{%s}publisher' % NS_DCTERMS), 'text',
                                 self.publisher)
        locations = xml.findall('.//{%s}location' % NS_SLTERMS)
        for location in locations:
            uri = getattr(location, 'text', self.locations)
            if uri and uri not in self.locations:
                self.locations.append(uri)

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
        template = open(self._template).read()
        self._updateLocationsXml()
        return template % self.__dict__

    def _updateLocationsXml(self):
        self._locations_xml = self._getLocationsAsXml()

    def _getLocationsAsXml(self):
        joint = '\n        '
        return joint.join([copy.copy(self._locations_xml) % {'location':location} 
                           for location in self.locations])

    def __str__(self):
        sortedKeys = []
        for k in self.__dict__:
            if not k.startswith('_') and not callable(k):
                sortedKeys.append(k)
        sortedKeys.sort()

        output = '* %s:\n' % self.__class__.__name__
        for k in sortedKeys:
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
