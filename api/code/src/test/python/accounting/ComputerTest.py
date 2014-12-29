#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2013, SixSq Sarl
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

import time
import xml.etree.ElementTree as ET
from mock import Mock
import unittest

import stratuslab.accounting.Computer
from stratuslab.accounting.Computer import Computer, PDiskHelper, \
    bytes_to_giga_approximation, ManifestGetFromMarketplaceError
from stratuslab.volume_manager.PersistentDisk import PersistentDisk

USAGERECORD_XML = """
<usagerecord>
  <vm id="0">
    <name>one-0</name>
    <time>1</time>
    <cpu>1.0</cpu>
    <mem>1024</mem>
    <net_rx>%(1GB)s</net_rx>
    <net_tx>%(1GB)s</net_tx>
    <starttime>2014-01-21 11:38:35</starttime>
    <endtime>1970-01-01 00:00:00</endtime>
    <disk>
      <size>1</size>
    </disk>
    <disk>
      <size>1.0</size>
    </disk>
  </vm>
</usagerecord>
""" % {'1GB': 1024 ** 3}

# Ony time related elements as returned by 'oneacct' CLI.
VM_XML = """
<vm>
  <time></time>
  <slice>

    <!-- Pending -->
    <stime>0</stime>

    <!-- Prolog -->
    <pstime>0</pstime>
    <petime>0</petime>

    <!-- Running -->
    <rstime>0</rstime>
    <retime>0</retime>

    <!-- Epilog -->
    <estime>0</estime>
    <eetime>0</eetime>

    <!-- Done -->
    <etime>0</etime>

  </slice>
</vm>
"""

HOUR = 60 * 60

DISK_SIZE = 10 * 1024 ** 3
IMAGE_MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<metadata>
    <rdf:RDF xmlns:dcterms="http://purl.org/dc/terms/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:slreq="http://mp.stratuslab.eu/slreq#" xmlns:slterms="http://mp.stratuslab.eu/slterms#" xml:base="http://mp.stratuslab.eu/">
        <rdf:Description rdf:about="#Pd1C0IktTPRXFPGlEHfxrF7gxOF">
            <dcterms:identifier>Pd1C0IktTPRXFPGlEHfxrF7gxOF</dcterms:identifier>
            <slreq:bytes>%s</slreq:bytes>
        </rdf:Description>
    </rdf:RDF>
</metadata>""" % DISK_SIZE


class ComputerTest(unittest.TestCase):

    def setUp(self):
        self.w_end = time.time() - HOUR
        self.w_start = self.w_end - 24 * HOUR

    def test_compute_totals(self):
        cmptr = Computer(0, 0, '', True)
        root = ET.fromstring(USAGERECORD_XML)
        cmptr.compute_totals(root)

        assert '1' == root.get('total_time')
        assert '1' == root.get('total_cpu')
        assert '1' == root.get('total_ram')
        assert '2' == root.get('total_disk')
        assert '1' == root.get('total_net_rx')
        assert '1' == root.get('total_net_tx')

    def test_update_time_on_vm_started_before_still_running(self):
        "Started before the metering window and still running."
        stime = int(self.w_start - HOUR)
        etime = 0
        vm = self._get_vm(stime, etime)
        delta_time_hours = int((self.w_end - self.w_start) / HOUR)

        self._update_and_assert(vm, delta_time_hours)

    def test_update_time_on_vm_started_before_ended_within(self):
        "Started before and ended within the metering window."
        stime = int(self.w_start - HOUR)
        etime = int(self.w_start + HOUR) + 1
        vm = self._get_vm(stime, etime)
        delta_time_hours = int((etime - self.w_start) / HOUR)

        self._update_and_assert(vm, delta_time_hours)

    def test_update_time_on_vm_started_ended_within(self):
        "Started and ended within the metering window."
        stime = int(self.w_start + HOUR)
        etime = stime + HOUR
        vm = self._get_vm(stime, etime)
        delta_time_hours = int((etime - stime) / HOUR)

        self._update_and_assert(vm, delta_time_hours)

    def test_update_time_on_vm_started_within_still_running(self):
        "Started within the metering window and still running."
        stime = int(self.w_end - HOUR)
        etime = 0
        vm = self._get_vm(stime, etime)
        delta_time_hours = int((self.w_end - stime) / HOUR)

        self._update_and_assert(vm, delta_time_hours)

    def test_update_time_on_vm_accepted_within_didnot_running(self):
        "Started within the metering window and still running."
        vm = self._get_vm(int(self.w_end - HOUR), 0)
        self._update_and_assert(vm, 1)

    def test_vm_in_range_ended_before(self):
        etime = int(self.w_start - HOUR)
        stime = etime - HOUR
        vm = self._get_vm(stime, etime)
        cmptr = Computer(self.w_start, self.w_end, '', True)
        assert False == cmptr.vm_in_range(vm)

    def test_vm_in_range_started_after(self):
        stime = int(self.w_end + HOUR)
        etime = stime + HOUR
        vm = self._get_vm(stime, etime)
        cmptr = Computer(self.w_start, self.w_end, '', True)
        assert False == cmptr.vm_in_range(vm)

    def test_vm_in_range_started_before_still_running(self):
        stime = int(self.w_start - HOUR)
        etime = 0
        vm = self._get_vm(stime, etime)
        cmptr = Computer(self.w_start, self.w_end, '', True)
        cmptr._query_etime_from_vm_details = cmptr.get_etime
        assert True == cmptr.vm_in_range(vm)

    def test_vm_in_range_accepted_within_didnot_run(self):
        vm = self._get_vm(0, 0)
        stime = int(self.w_end - HOUR)
        vm.find('slice/' + Computer.VM_STARTTIME_ELEM).text = str(stime)
        cmptr = Computer(self.w_start, self.w_end, '', True)
        cmptr._query_etime_from_vm_details = cmptr.get_etime
        assert True == cmptr.vm_in_range(vm)

    def test_vm_in_range_accepted_before_didnot_run(self):
        vm = self._get_vm(0, 0)
        stime = int(self.w_start - HOUR)
        vm.find('slice/' + Computer.VM_STARTTIME_ELEM).text = str(stime)
        cmptr = Computer(self.w_start, self.w_end, '', True)
        cmptr._query_etime_from_vm_details = cmptr.get_etime
        assert False == cmptr.vm_in_range(vm)

    def test_vm_in_range_accepted_after_didnot_run(self):
        vm = self._get_vm(0, 0)
        stime = int(self.w_end + HOUR)
        vm.find('slice/' + Computer.VM_STARTTIME_ELEM).text = str(stime)
        cmptr = Computer(self.w_start, self.w_end, '', True)
        cmptr._query_etime_from_vm_details = cmptr.get_etime
        assert False == cmptr.vm_in_range(vm)

    def test_get_size_from_marketplace(self):
        cmptr = Computer(self.w_start, self.w_end, '', True)
        _url_get_save = stratuslab.accounting.Computer.url_get
        try:
            stratuslab.accounting.Computer.url_get = Mock(return_value=IMAGE_MANIFEST)
            size_gb = bytes_to_giga_approximation(DISK_SIZE)
            assert size_gb == cmptr.get_size_from_marketplace_or_pdisk_by_manifest_id('http://foo.bar/baz')
            assert size_gb == cmptr.marketplace_size_cache['http://foo.bar/baz']
        finally:
            stratuslab.accounting.Computer.url_get = _url_get_save

    def test_get_size_from_pdisk_by_manifest_id(self):
        cmptr = Computer(self.w_start, self.w_end, '', True)
        size_gb = bytes_to_giga_approximation(DISK_SIZE)
        _get_size_saved = stratuslab.accounting.Computer.MPHelper.get_size
        _get_size_by_marketplace_url_saved = \
            stratuslab.accounting.Computer.PDiskHelper.get_size_by_marketplace_url
        try:
            stratuslab.accounting.Computer.MPHelper.get_size = \
                Mock(side_effect=ManifestGetFromMarketplaceError('Moked exception.'))
            stratuslab.accounting.Computer.PDiskHelper.get_size_by_marketplace_url = \
                Mock(return_value=size_gb)
            assert size_gb == cmptr.get_size_from_marketplace_or_pdisk_by_manifest_id('http://foo.bar/baz')
            assert size_gb == cmptr.marketplace_size_cache['http://foo.bar/baz']
        finally:
            stratuslab.accounting.Computer.MPHelper.get_size = _get_size_saved
            stratuslab.accounting.Computer.PDiskHelper.get_size_by_marketplace_url = \
                _get_size_by_marketplace_url_saved

    def test_get_size_from_pdisk(self):
        cmptr = Computer(self.w_start, self.w_end, '', True)
        _get_config_as_dict_saved = \
            stratuslab.accounting.Computer.PDiskHelper._get_config_as_dict
        try:
            stratuslab.accounting.Computer.PDiskHelper._get_config_as_dict = \
                Mock(return_value={'pdiskEndpoint': 'foo-endpoint', 'persistentDiskCloudServiceUser': 'bar-user'})
            PersistentDisk.getValue = Mock(return_value='2048')
            assert 2048 == cmptr.get_size_from_pdisk('foo:1.2.3.4:1234:1-2-3-4')
            assert 2048 == cmptr.pdisk_size_cache['foo:1.2.3.4:1234:1-2-3-4']
        finally:
            stratuslab.accounting.Computer.PDiskHelper._get_config_as_dict = \
                _get_config_as_dict_saved

    def test__get_pdisk_endpoint_and_disk_uuid_from_uri(self):
        endpoint, uuid = PDiskHelper.get_endpoint_and_disk_uuid_from_uri('foo:1.2.3.4:1234:1-2-3-4')
        assert endpoint == '1.2.3.4:1234'
        assert uuid == '1-2-3-4'

        endpoint, uuid = PDiskHelper.get_endpoint_and_disk_uuid_from_uri('foo:1.2.3.4:1-2-3-4')
        assert endpoint == '1.2.3.4'
        assert uuid == '1-2-3-4'

        self.assertRaises(Exception,
                          PDiskHelper.get_endpoint_and_disk_uuid_from_uri,
                          ('foo:bar',))

    def test_get_disk_size_with_MP_swap_PDisk_disks(self):
        cmptr = Computer(self.w_start, self.w_end, '', True)
        with open('vm-with-extra-disk-in-pdisk.xml') as f:
            vm = ET.fromstring(f.read())
        disks = cmptr.get_disks(vm)
        assert 3 == len(disks)
        disk_MP, disk_swap, disk_pdisk = disks

        # Disk from Marketplace (11GB)
        _url_get_save = stratuslab.accounting.Computer.url_get
        stratuslab.accounting.Computer.url_get = Mock(return_value=IMAGE_MANIFEST)
        try:
            size_gb = bytes_to_giga_approximation(DISK_SIZE)
            assert size_gb == cmptr.get_disk_size(disk_MP)
            assert size_gb == \
                cmptr.marketplace_size_cache['https://marketplace.stratuslab.eu/metadata/Pd1C0IktTPRXFPGlEHfxrF7gxOF']
        finally:
            stratuslab.accounting.Computer.url_get = _url_get_save

        # swap (1.5GB)
        assert float('1536') / 1024 == cmptr.get_disk_size(disk_swap)

        # disk from PDisk (2TB)
        _get_config_as_dict_saved = \
            stratuslab.accounting.Computer.PDiskHelper._get_config_as_dict
        try:
            stratuslab.accounting.Computer.PDiskHelper._get_config_as_dict = \
                Mock(return_value={'pdiskEndpoint': 'foo-endpoint', 'persistentDiskCloudServiceUser': 'bar-user'})
            PersistentDisk.getValue = Mock(return_value='2048')
            assert 2048 == cmptr.get_disk_size(disk_pdisk)
            assert 2048 == cmptr.pdisk_size_cache['pdisk:154.48.152.10:8445/95b75092-17d2-459f-9fa0-cd1deaa721f1']
        finally:
            stratuslab.accounting.Computer.PDiskHelper._get_config_as_dict = \
                _get_config_as_dict_saved

    def _get_vm(self, stime, etime):
        vm = ET.fromstring(VM_XML)
        vm.find('slice/' + Computer.VM_RUN_STARTTIME_ELEM).text = str(stime)
        vm.find('slice/' + Computer.VM_RUN_ENDTIME_ELEM).text = str(etime)
        return vm

    def _update_and_assert(self, vm, delta_time_hours):
        cmptr = Computer(self.w_start, self.w_end, '', True)
        cmptr._query_etime_from_vm_details = cmptr.get_etime
        cmptr._update_time_on_vm(vm)
        assert delta_time_hours == int(vm.find('time').text)


if __name__ == "__main__":
    unittest.main()
