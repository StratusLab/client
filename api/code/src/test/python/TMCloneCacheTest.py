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

from stratuslab.tm.TMCloneCache import TMCloneCache
from stratuslab import Util

class TMCloneCacheTest(unittest.TestCase):

    CONFIG_FILE = """[default]
persistent_disk_ip = 127.0.0.1
persistent_disk_lvm_device = /dev/pdisk
one_username = oneadmin
one_password = oneadmin
one_port = 2633
persistent_disk_public_base_url = https://example.com:8445
"""

    def setUp(self):
        self._write_conf_file()

    def tearDown(self):
        os.unlink(self.conf_filename)

    def testInit(self):
        tm = TMCloneCache({TMCloneCache._ARG_SRC_POS : 'foo:bar',
                           TMCloneCache._ARG_DST_POS : 'foo:bar',
                           'bar' : 'baz'},
                           conf_filename=self.conf_filename)
        self.assertEqual(tm.pdiskEndpoint, '127.0.0.1')
        self.assertEqual(tm.persistentDiskIp, '127.0.0.1')

    def test_checkAuthorization(self):
        tm = TMCloneCache({TMCloneCache._ARG_SRC_POS : 'foo:bar',
                           TMCloneCache._ARG_DST_POS : 'foo:bar',
                           'bar' : 'baz'},
                           conf_filename=self.conf_filename)

        tm._deriveVMOwner = Mock(return_value='jayrandom')
        tm._getDiskOwner = Mock(return_value='jayrandom')
        tm._getDiskVisibility = Mock(return_value='whatever')
        try:
            tm._checkAuthorization()
        except ValueError:
            self.fail('Should not have thrown ValueError')

        tm._deriveVMOwner = Mock(return_value='jayrandom')
        tm._getDiskOwner = Mock(return_value='jayrandom')
        tm._getDiskVisibility = Mock(return_value=tm._DISK_UNAUTHORIZED_VISIBILITIES[0])
        try:
            tm._checkAuthorization()
        except ValueError:
            self.fail('Should not have thrown ValueError')

        tm._deriveVMOwner = Mock(return_value='jayrandom')
        tm._getDiskOwner = Mock(return_value='johndoe')
        tm._getDiskVisibility = Mock(return_value='whatever')
        try:
            tm._checkAuthorization()
        except ValueError:
            self.fail('Should not have thrown ValueError')

        tm._deriveVMOwner = Mock(return_value='jayrandom')
        tm._getDiskOwner = Mock(return_value='johndoe')
        tm._getDiskVisibility = Mock(return_value=tm._DISK_UNAUTHORIZED_VISIBILITIES[0])
        self.failUnlessRaises(ValueError, tm._checkAuthorization)

        tm._deriveVMOwner = Mock(return_value='jayrandom')
        tm._getDiskOwner = Mock(return_value=tm._PDISK_SUPERUSER)
        tm._getDiskVisibility = Mock(return_value=tm._DISK_UNAUTHORIZED_VISIBILITIES[0])
        try:
            tm._checkAuthorization()
        except ValueError:
            self.fail('Should not have thrown ValueError')

    def test_updatePDiskSrcUrlFromPublicToLocalIp(self):
        tm = TMCloneCache({TMCloneCache._ARG_SRC_POS : 'foo:bar',
                           TMCloneCache._ARG_DST_POS : 'foo:bar',
                           'bar' : 'baz'},
                           conf_filename=self.conf_filename)
        assert 'https://example.com:8445' == tm.persistentDiskPublicBaseUrl
        tm.diskSrc = 'pdisk:%s:uuid-123' % Util.getHostnamePortFromUri(
                                                tm.persistentDiskPublicBaseUrl)
        tm._updatePDiskSrcUrlFromPublicToLocalIp()
        assert 'pdisk:127.0.0.1:8445:uuid-123' == tm.diskSrc

        # The URI shouldn't be updated when it points to an IP different to the public one.
        tm._updatePDiskSrcUrlFromPublicToLocalIp()
        assert 'pdisk:127.0.0.1:8445:uuid-123' == tm.diskSrc

    # Utils
    def _write_conf_file(self):
        fd, self.conf_filename = tempfile.mkstemp()
        os.write(fd, self.CONFIG_FILE)
        os.close(fd)
        
if __name__ == "__main__":
    unittest.main()
