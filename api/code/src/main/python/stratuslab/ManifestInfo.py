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

NS_RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
NS_DCTERMS = 'http://purl.org/dc/terms/'
NS_SLTERMS = 'http://mp.stratuslab.eu/slterms#'
NS_SLREQ = 'http://mp.stratuslab.eu/slreq#'

imageTypes = ['base', 'grid']
imageKinds = ('machine', 'disk')
imageFormats = ['raw', 'qcow2']


class ManifestInfo(object):
    NS_RDF = NS_RDF
    NS_DCTERMS = NS_DCTERMS
    NS_SLTERMS = NS_SLTERMS
    NS_SLREQ = NS_SLREQ

    IMAGE_VALIDITY = (356 / 2) * 24 * 3600 # 1/2 year in sec

    MANDATORY_CHECKSUMS = ('sha1',)
    CHECKSUM_NAMES = ('md5', 'sha1', 'sha256', 'sha512')

    DISKS_BUS_DEFAULT = 'ide'
    INBOUND_PORTS_DEFAULT = []

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
        self.title = ''
        self.tag = ''
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

        self.disksbus = ManifestInfo.DISKS_BUS_DEFAULT
        self.inboundports = ManifestInfo.INBOUND_PORTS_DEFAULT

        self.verboseLevel = 0

        configHolder.assign(self)

        self._template = Util.get_share_file(['template', 'manifest.xml.tpl'])

        self._manifestTemplateElements = \
            (('type', 'type', NS_DCTERMS, None),
             ('created', 'created', NS_DCTERMS, None),
             ('valid', 'valid', NS_DCTERMS, None),
             ('title', 'title', NS_DCTERMS, ''),
             ('tag', 'alternative', NS_DCTERMS, ''),
             ('comment', 'description', NS_DCTERMS, None),
             ('compression', 'compression', NS_DCTERMS, None),
             ('creator', 'creator', NS_DCTERMS, self.creator),
             ('user', 'creator', NS_DCTERMS, self.creator),
             ('format', 'format', NS_DCTERMS, self.format),
             ('publisher', 'publisher', NS_DCTERMS, self.publisher),
             ('os', 'os', NS_SLTERMS, None),
             ('arch', 'os-arch', NS_SLTERMS, None),
             ('osversion', 'os-version', NS_SLTERMS, None),
             ('version', 'version', NS_SLTERMS, None),
             ('kind', 'kind', NS_SLTERMS, self.kind),
             ('disksbus', 'disks-bus', NS_SLTERMS, self.disksbus),
             ('hypervisor', 'hypervisor', NS_SLTERMS, self.hypervisor),
             ('email', 'email', NS_SLREQ, self.email))

    @staticmethod
    def addElementToManifest(root, elementName, value):
        elems = root.findall('.//{%s}%s' % (ManifestInfo.NS_SLTERMS, elementName))

        if elems:
            # Check if already present. If yes, do nothing.
            for elem in elems:
                if elem.text and elem.text == value:
                    Util.printWarning(
                        "Element '%s' with value '%s' already defined in the manifest. Skipping addition of the element." % \
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
            xml_tree = Util.etree_from_text(manifest)
        except SyntaxError, ex:
            raise ExecutionException('Unable to parse manifest: %s\nMANIFEST:\n%s' %
                                     (str(ex), manifest))

        self.parseManifestFromXmlTree(xml_tree)

    def _setEndorserFromXmlTree(self, xml_tree):
        xpathPrefix = './/{http://mp.stratuslab.eu/slreq#}%s/{http://mp.stratuslab.eu/slreq#}'
        self.endorser = xml_tree.findtext(xpathPrefix % 'endorser' + 'email')

    def _setRequiredAttributesFromXmlTree(self, xml_tree):
        """Attributes required by Schema."""

        for elem, ns in [('identifier', NS_DCTERMS), ('bytes', NS_SLREQ)]:
            try:
                val = getattr(xml_tree.find('.//{%s}%s' % (ns, elem)), 'text')
            except AttributeError:
                raise ExecutionException(
                    "Missing mandatory element '%s' in namespace '%s'" % (elem, ns))
            else:
                attr = elem
                setattr(self, attr, val)

        checksums = xml_tree.findall('.//{%s}checksum' % NS_SLREQ)
        for checksum in checksums:
            checkSumType = checksum.find('.//{%s}algorithm' % NS_SLREQ).text
            checkSumType = _normalizeForInstanceAttribute(checkSumType)
            checkSumValue = checksum.find('.//{%s}value' % NS_SLREQ).text
            setattr(self, checkSumType, checkSumValue)


    def _setClientXmlTemplateAttributesFromXmlTree(self, xml_tree):
        """Attributes from client XML template."""

        for attrObj, elemXml, ns, default in self._manifestTemplateElements:
            try:
                attrVal = getattr(xml_tree.find('.//{%s}%s' % (ns, elemXml)), 'text')
            except AttributeError:
                if default != None:
                    attrVal = default
                else:
                    raise ExecutionException("Missing element '%s' in namespace '%s'" % (elemXml, ns))
            else:
                setattr(self, attrObj, attrVal)


    def _setLocationFromXmlTree(self, xml_tree):
        locations = xml_tree.findall('.//{%s}location' % NS_SLTERMS)
        for location in locations:
            uri = getattr(location, 'text', self.locations)
            if uri and uri not in self.locations:
                self.locations.append(uri)

    def _setInboundPortsFromXmlTree(self, xml_tree):
        ports = xml_tree.findall('.//{%s}inbound-port' % NS_SLTERMS)
        for port in ports:
            if hasattr(port, 'text') and port.text not in self.inboundports:
                self.inboundports.append(port.text)

    def parseManifestFromXmlTree(self, xml_tree):

        self._setEndorserFromXmlTree(xml_tree)
        self._setRequiredAttributesFromXmlTree(xml_tree)
        self._setClientXmlTemplateAttributesFromXmlTree(xml_tree)
        self._setLocationFromXmlTree(xml_tree)
        self._setInboundPortsFromXmlTree(xml_tree)

        self.created = getattr(xml_tree.find('.//{%s}endorsement/{%s}created' % (NS_SLREQ, NS_DCTERMS)), 'text',
                               self.created)

    def parseManifestFromFile(self, filename):
        manifest = file(filename).read()
        self.parseManifest(manifest)

    def buildAndSave(self, filename=''):
        manifestText = self.build()
        if not filename:
            filename = '%s-%s-%s-%s-%s%s' % (self.os, self.osversion,
                                             self.arch, self.type,
                                             self.version, Util.manifestExt)
        Util.filePutContent(filename, manifestText)
        Util.printDetail("Manifest: %s" % filename, self.verboseLevel,
                         Util.VERBOSE_LEVEL_DETAILED)

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
        return joint.join([copy.copy(self._locations_xml) % {'location': location}
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
    for i, v in enumerate(encoding):
        decoding[v] = long(i)

    sha1Bits = 160
    fieldBits = 6
    identifierChars = sha1Bits / fieldBits + 1
    divisor = long(2) ** fieldBits

    def sha1ToIdentifier(self, sha1):
        try:
            sha1 = long(sha1, 16)
            sb = ''
            for _ in range(self.identifierChars):
                values = divmod(sha1, self.divisor)
                sha1 = values[0]
                sb += self.encoding[int(values[1])]
            return sb[::-1]
        except ValueError as e:
            raise ValueError('invalid SHA-1 checksum: %s' % sha1)

    def identifierToSha1(self, identifier):
        sha1 = long(0)
        for i in range(len(identifier)):
            sha1 = sha1 << self.fieldBits
            bits = long(self.decoding[identifier[i:i + 1]])
            sha1 = sha1 | bits
        return hex(sha1).lstrip('0x').rstrip('L')


def _normalizeForInstanceAttribute(attr):
    return _removeDashes(attr.lower())


def _removeDashes(string):
    return re.sub('-', '', string)
