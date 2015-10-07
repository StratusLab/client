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

from mock.mock import Mock

import stratuslab.ConfigHolder as ConfigHolder
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.vm_manager.Runner import Runner


class RunnerTest(unittest.TestCase):

    MANIFEST_DISKS_BUS_IDE = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
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
        <dcterms:valid>2011-01-24T09:59:42Z</dcterms:valid>
        <dcterms:description>test</dcterms:description>
        <dcterms:compression>test</dcterms:compression>
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

    MANIFEST_DISKS_BUS_VIRTIO = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcterms="http://purl.org/dc/terms/" xmlns:slreq="http://mp.stratuslab.eu/slreq#"
    xmlns:slterms="http://mp.stratuslab.eu/slterms#" xml:base="http://mp.stratuslab.eu/">

    <rdf:Description rdf:about="#MMZu9WvwKIro-rtBQfDk4PsKO7_">

        <dcterms:identifier>MMZu9WvwKIro-rtBQfDk4PsKO7_</dcterms:identifier>

        <slterms:disks-bus>virtio</slterms:disks-bus>

        <slterms:os>linux</slterms:os>
        <slterms:os-arch>linux</slterms:os-arch>
        <slterms:os-version>0.1</slterms:os-version>
        <slreq:bytes>0</slreq:bytes>
        <dcterms:type>machine</dcterms:type>
        <dcterms:valid>2011-01-24T09:59:42Z</dcterms:valid>
        <dcterms:description>test</dcterms:description>
        <dcterms:compression>test</dcterms:compression>
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
        Runner._setCloudContext = Mock()
        self.ch = ConfigHolder.ConfigHolder()

    def tearDown(self):
        reload(ConfigHolder)

    def test_set_root_disk_size(self):
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_VIRTIO,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('size = 0,', vm_params['root_disk_size_entry'])

    def testDisksBusTypeVirtio(self):
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_VIRTIO,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('vd', vm_params['vm_disks_prefix'])

    def testDisksBusTypeIde(self):
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_IDE,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('hd', vm_params['vm_disks_prefix'])

    def testDisksBusTypeExtraDiskIde(self):
        self.ch.set('extraDiskSize', '1')
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_IDE,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        extra_disk = Runner.EXTRA_DISK % {'extraDiskSize' : '1',
                                          'vm_disks_prefix' : 'hd'}
        self.failUnlessEqual(extra_disk, vm_params['extra_disk'])

    def testDisksBusTypeExtraDiskVirtio(self):
        self.ch.set('extraDiskSize', '1')
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_VIRTIO,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        extra_disk = Runner.EXTRA_DISK % {'extraDiskSize' : '1',
                                          'vm_disks_prefix' : 'vd'}
        self.failUnlessEqual(extra_disk, vm_params['extra_disk'])

    def testDisksBusTypeReadonlyDiskIde(self):
        uuid = 'f25cd0dc-e56f-4eea-be0c-88d866a2c73c'
        self.ch.set('readonlyDiskId', uuid)
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_IDE,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        readonly_disk = Runner.READONLY_DISK % {'readonlyDiskId' : uuid,
                                                'vm_disks_prefix' : 'hd'}
        self.failUnlessEqual(readonly_disk, vm_params['readonly_disk'])

    def testDisksBusTypeReadonlyDiskVirtio(self):
        uuid = 'f25cd0dc-e56f-4eea-be0c-88d866a2c73c'
        self.ch.set('readonlyDiskId', uuid)
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_VIRTIO,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        readonly_disk = Runner.READONLY_DISK % {'readonlyDiskId' : uuid,
                                                'vm_disks_prefix' : 'vd'}
        self.failUnlessEqual(readonly_disk, vm_params['readonly_disk'])

    def testDisksBusTypeFromCommandLineIde(self):
        self.ch.set('vmDisksBus', 'ide')
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_VIRTIO,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('hd', vm_params['vm_disks_prefix'])

    def testDisksBusTypeFromCommandLineVirtio(self):
        self.ch.set('vmDisksBus', 'virtio')
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_IDE,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('vd', vm_params['vm_disks_prefix'])

    def testDisksBusTypeFromCommandLineScsi(self):
        self.ch.set('vmDisksBus', 'scsi')
        runner = self._getRunnerForManifest(self.MANIFEST_DISKS_BUS_VIRTIO,
                                            'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('sd', vm_params['vm_disks_prefix'])

    def _getRunnerForManifest(self, manifest, imageid):
        self._mockManifestDownloader(manifest)
        self.ch.set('verboseLevel', 0)
        return Runner(imageid, self.ch)

    @staticmethod
    def _mockManifestDownloader(manifest):
        mock = Mock(return_value = ManifestDownloader._parseXml(manifest))
        ManifestDownloader._download = mock

if __name__ == "__main__":
    unittest.main()
