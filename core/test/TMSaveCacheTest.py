#!/usr/bin/env python
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, SixSq Sarl
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
import unittest
import os
import tempfile
from mock.mock import Mock
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.ManifestInfo import ManifestInfo
from stratuslab.tm.TMSaveCache import TMSaveCache
from stratuslab.Signator import Signator
import sys

class TMSaveCacheTest(unittest.TestCase):

    CONFIG_FILE = """[default]
persistent_disk_ip = 127.0.0.1
one_username = oneadmin
one_password = oneadmin
one_port = 2633
"""
    TEST_MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcterms="http://purl.org/dc/terms/" xmlns:slreq="http://mp.stratuslab.eu/slreq#"
    xmlns:slterms="http://mp.stratuslab.eu/slterms#" xml:base="http://mp.stratuslab.eu/">

    <rdf:Description rdf:about="#MMZu9WvwKIro-rtBQfDk4PsKO7_">

        <dcterms:identifier>MMZu9WvwKIro-rtBQfDk4PsKO7_</dcterms:identifier>

        <slterms:os>linux</slterms:os>
        <slterms:os-arch>linux</slterms:os-arch>
        <slterms:os-version>0.1</slterms:os-version>
        <slreq:bytes>0</slreq:bytes>
        <dcterms:type>machine</dcterms:type>
        <dcterms:valid>1970-01-01T00:00:00Z</dcterms:valid>
        <dcterms:description>test manifest</dcterms:description>
        <dcterms:compression>gz</dcterms:compression>
        <slterms:version>1.0</slterms:version>
        <slreq:endorsement rdf:parseType="Resource">
            <dcterms:created>2011-01-24T09:59:42Z</dcterms:created>
            <slreq:endorser rdf:parseType="Resource">
                <slreq:email>jane.tester@example.org</slreq:email>
                <slreq:subject>CN=Jane Tester,OU=Testing Department,O=StratusLab Project,C=EU</slreq:subject>
                <slreq:issuer>CN=Jane Tester,OU=Testing Department,O=StratusLab Project,C=EU</slreq:issuer>
            </slreq:endorser>
        </slreq:endorsement>

    </rdf:Description>
</rdf:RDF>
"""

    def setUp(self):
        self._write_conf_file()

    def tearDown(self):
        os.unlink(self.conf_filename)

    def testInit(self):
        tm = TMSaveCache({}, conf_filename=self.conf_filename)
        self.assertEquals(tm.pdiskEndpoint, '127.0.0.1')
        self.assertEquals(tm.persistentDiskIp, '127.0.0.1')

    def testParseArgs(self):
        tm = TMSaveCache({TMSaveCache._ARG_SRC_POS : 'foo'},
                         conf_filename=self.conf_filename)
        self.failUnlessRaises(ValueError, tm._parseArgs)

        tm = TMSaveCache({TMSaveCache._ARG_SRC_POS : 'foo:bar'},
                         conf_filename=self.conf_filename)
        tm._parseArgs()
        self.assertEquals(tm.diskSrcHost, 'foo')
        self.assertEquals(tm.diskSrcPath, 'bar')

    def testRetrieveInstanceId(self):
        tm = TMSaveCache({},
                         conf_filename=self.conf_filename)

        for path in ['foo', '/a/b', '/1/2']:
            tm.diskSrcPath = path
            self.failUnlessRaises(ValueError, tm._retrieveInstanceId)

        for path in ['/a/1', '/a/1/b']:
            tm.diskSrcPath = path
            tm._retrieveInstanceId()
            self.failUnlessEqual(tm.instanceId, 1)

    def testGenerateManifest(self):
        manifest_info = ManifestInfo()
        manifest_info.parseManifest(self.TEST_MANIFEST)
        ManifestDownloader.getManifestInfo = Mock(return_value = manifest_info)

        PDISK_ENDPOINT = 'pdisk:0.0.0.0:8445'

        TMSaveCache._getPDiskServerInfo = Mock(return_value = PDISK_ENDPOINT+':48ac4190-9a11-4a06-8bef-03fd97080eba')

        tm = TMSaveCache({TMSaveCache._ARG_SRC_POS : 'foo:/bar/1'},
                         conf_filename=self.conf_filename)
        tm._parseArgs()
        tm._retrievePDiskInfo()
        tm.createImageInfo = {'creatorEmail':'jrandom@tester.org',
                              'creatorName':'Jay Random',
                              'newImageComment':'test',
                              'newImageVersion':'0.0',
                              'newImageMarketplace':'http://new.markeplace.org'}
        tm.imageSha1 = 'ea7d0ddf7af4e2ea431db89639feb7036fb23062'
        tm.createdPDiskId = 'foo-bar-baz'

        try:
            tm._generateP12Cert()
            self.failUnless(os.path.exists(tm.p12cert))

            tm._generateP12Cert()
            tm._retrieveManifestsPath()
            tm.pdiskPathNew = tm._buildPDiskPath(tm.createdPDiskId)
            tm._buildAndSaveManifest()
            self.failUnless(os.path.exists(tm.manifestNotSignedPath))
            
            minfo = ManifestInfo()
            minfo.parseManifestFromFile(tm.manifestNotSignedPath)
            assert minfo.comment == 'test'
            assert minfo.creator == 'Jay Random'
            assert minfo.version == '0.0'
            assert minfo.sha1 == tm.imageSha1
            assert minfo.locations == [PDISK_ENDPOINT+':foo-bar-baz']

            self.failUnless('New image created' in str(tm._composeEmailToUser()))

            if not Signator.findJar():
                print "Skipping signature sub-test as Signator jar can not be found."
                return
            tm._signManifest()
            self.failUnless(os.path.exists(tm.manifestPath))
        finally:
            tm._cleanup()

    # Utils
    def _write_conf_file(self):
        fd, self.conf_filename = tempfile.mkstemp()
        os.write(fd, self.CONFIG_FILE)
        os.close(fd)
        
if __name__ == "__main__":
    unittest.main()