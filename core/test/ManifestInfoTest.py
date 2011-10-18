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
import unittest

from stratuslab.ManifestInfo import ManifestInfo, ManifestIdentifier
from stratuslab.Exceptions import ExecutionException
from stratuslab.Util import importETree

etree = importETree()

class ManifestInfoTest(unittest.TestCase):

    rdfFullTemplate = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:slterms="http://mp.stratuslab.eu/slterms#"
    xmlns:slreq="http://mp.stratuslab.eu/slreq#"
    xml:base="http://mp.stratuslab.eu/">

    <rdf:Description rdf:about="#MMZu9WvwKIro-rtBQfDk4PsKO7_">

        <dcterms:identifier>MMZu9WvwKIro-rtBQfDk4PsKO7_</dcterms:identifier>

        <slreq:bytes>100</slreq:bytes>

        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>MD5</slreq:algorithm>
            <slreq:value>ec434ef8a756cf4787e39247abcc8382</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-1</slreq:algorithm>
            <slreq:value>c319bbd5afc0a22ba3eaed0507c39383ec28eeff</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-256</slreq:algorithm>
            <slreq:value>fb84224a5b7a788549a64a01185c961a2894b9c4142fecfa4cffb20eff433cec</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-512</slreq:algorithm>
            <slreq:value>816e6f78364c814701f6497dd3e3e076ba25754560cff489b33ca2e46889ad4ec14497fb6fce11fb7631b006e7621b2442a7da7fe6a92fc888ea6d9097b9e453</slreq:value>
        </slreq:checksum>

        <slreq:endorsement rdf:parseType="Resource"/>

        <dcterms:created>2011-01-24T09:59:42Z</dcterms:created>
        <dcterms:creator>Charles LOOMIS</dcterms:creator>

        <dcterms:type>machine</dcterms:type>
        <dcterms:valid>2011-07-23T10:59:42+0200</dcterms:valid>
        <dcterms:publisher>%(publisher)s</dcterms:publisher>
        <dcterms:title>ttylinux-9.7-i486-base-1.1</dcterms:title>
        <dcterms:description>A 32-bit ttylinux image that follows the standard
            StratusLab contextualization strategy.</dcterms:description>
        <slterms:version>1.0</slterms:version>
        <slterms:serial-number>0</slterms:serial-number>
        <slterms:os>ttylinux</slterms:os>
        <slterms:os-version>9.7</slterms:os-version>
        <slterms:os-arch>i486</slterms:os-arch>
        <slterms:hypervisor>kvm</slterms:hypervisor>
        
        <slterms:location>%(location1)s</slterms:location>
        <slterms:location>%(location2)s</slterms:location>

    </rdf:Description>
</rdf:RDF>
"""
    _publisher1 = 'StratusLab'
    _publisher2 = 'stratuslab'
    _location1_1 = 'http://example.com/exmaple.file.1'
    _location1_2 = 'http://example.com/exmaple.file.2'
    _location2_1 = 'http://test.com/test.file.1'
    _location2_2 = 'http://test.com/test.file.2'
    rdfFull1 = rdfFullTemplate % {'publisher':_publisher1, 'location1':_location1_1,
                                  'location2':_location1_2}
    rdfFull2 = rdfFullTemplate % {'publisher':_publisher2, 'location1':_location2_1,
                                  'location2':_location2_2}

    manifestDcFull = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
%s
""" % rdfFull1

    manifestDcMissingElemsMandatory = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:slterms="http://mp.stratuslab.eu/slterms#"
    xmlns:slreq="http://mp.stratuslab.eu/slreq#"
    xml:base="http://mp.stratuslab.eu/">

    <rdf:Description rdf:about="#MMZu9WvwKIro-rtBQfDk4PsKO7_">

        <dcterms:identifier>MMZu9WvwKIro-rtBQfDk4PsKO7_</dcterms:identifier>

    </rdf:Description>
</rdf:RDF>
"""
    manifestDcMissingElems = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:slterms="http://mp.stratuslab.eu/slterms#"
    xmlns:slreq="http://mp.stratuslab.eu/slreq#"
    xml:base="http://mp.stratuslab.eu/">

    <rdf:Description rdf:about="#MMZu9WvwKIro-rtBQfDk4PsKO7_">

        <dcterms:identifier>MMZu9WvwKIro-rtBQfDk4PsKO7_</dcterms:identifier>

        <slreq:bytes>100</slreq:bytes>

        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>MD5</slreq:algorithm>
            <slreq:value>ec434ef8a756cf4787e39247abcc8382</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-1</slreq:algorithm>
            <slreq:value>c319bbd5afc0a22ba3eaed0507c39383ec28eeff</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-256</slreq:algorithm>
            <slreq:value>fb84224a5b7a788549a64a01185c961a2894b9c4142fecfa4cffb20eff433cec</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-512</slreq:algorithm>
            <slreq:value>816e6f78364c814701f6497dd3e3e076ba25754560cff489b33ca2e46889ad4ec14497fb6fce11fb7631b006e7621b2442a7da7fe6a92fc888ea6d9097b9e453</slreq:value>
        </slreq:checksum>

        <slreq:endorsement rdf:parseType="Resource"/>

        <dcterms:created>2011-01-24T09:59:42Z</dcterms:created>
        <dcterms:creator>Charles LOOMIS</dcterms:creator>

    </rdf:Description>
</rdf:RDF>
"""
    def setUp(self):
        self.template = os.path.join(os.path.dirname(__file__),
                                       '../share/template/manifest.xml.tpl')

    def tearDown(self):
        self.template = ''

    def testGetInfo(self):
        infoDC = ManifestInfo()
        infoDC.parseManifest(ManifestInfoTest.manifestDcFull)

        self.assertEquals('2011-01-24T09:59:42Z', infoDC.created)

    def testUpdateManifest(self):

        info = ManifestInfo()
        info._template = self.template
        info.parseManifest(ManifestInfoTest.manifestDcFull)

        self.assertEquals('machine', info.type)
        info.type = 'disk'

        xml = info.tostring()
        info = ManifestInfo()
        info.template = self.template
        info.parseManifest(xml)

        self.assertEquals('disk', info.type)

    def testMissingElements(self):

        info = ManifestInfo()
        info._template = self.template
        self.failUnlessRaises(ExecutionException, info.parseManifest, 
                              ManifestInfoTest.manifestDcMissingElemsMandatory)

        info = ManifestInfo()
        info._template = self.template
        self.failUnlessRaises(ExecutionException, info.parseManifest, 
                              ManifestInfoTest.manifestDcMissingElems)

    def testListOfManifests(self):
        metadata = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<metadata>
%s
%s
</metadata>
""" % (self.rdfFull1, self.rdfFull2)
        info = ManifestInfo()
        info.parseManifest(metadata)
        
        self.failUnlessEqual(info.publisher, self._publisher1, "Failure in parsing list of manifests.")
        self.failUnlessEqual(info.locations, [self._location1_1, self._location1_2,
                                             self._location2_1, self._location2_2],
                                             "Failure in parsing list of manifests.")

    def testTostringWithListOfLocations(self):
        info1 = ManifestInfo()
        info1._template = self.template
        info1.parseManifest(self.rdfFull1)
        manifest = info1.tostring()
        
        info2 = ManifestInfo()
        info2.parseManifest(manifest)
        
        self.failUnlessEqual(info1.locations, info2.locations, 
                             "Lists of locations don't match. Serialization failed.")

    def testNonEmtpyLocations(self):
        info = ManifestInfo()
        info._template = self.template
        info.locations = ['location.foo']
        manifest = info.tostring()

        dom = etree.fromstring(manifest)
        locations = dom.findall('.//{%s}location' % ManifestInfo.NS_SLTERMS)
        location = getattr(locations[0], 'text', '')

        self.failUnlessEqual('location.foo', location,
                             "Failure in setting location element on ManifestInfo.")

class ManifestIdentifierTest(unittest.TestCase):

    def testConversion(self):
        sha1 = 'c319bbd5afc0a22ba3eaed0507c39383ec28eeff'
        id = ManifestIdentifier()
        self.assertEquals(int(sha1, 16),
                          int(id.identifierToSha1(id.sha1ToIdentifier(sha1)), 16))

if __name__ == "__main__":
    unittest.main()
