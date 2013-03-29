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

from stratuslab.tm.TMCloneCache import TMCloneCache

class TMCloneCacheTest(unittest.TestCase):

    CONFIG_FILE = """[default]
persistent_disk_ip = 127.0.0.1
persistent_disk_lvm_device = /dev/pdisk
one_username = oneadmin
one_password = oneadmin
one_port = 2633
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
        self.assertEquals(tm.pdiskEndpoint, '127.0.0.1')
        self.assertEquals(tm.persistentDiskIp, '127.0.0.1')

    # Utils
    def _write_conf_file(self):
        fd, self.conf_filename = tempfile.mkstemp()
        os.write(fd, self.CONFIG_FILE)
        os.close(fd)
        
if __name__ == "__main__":
    unittest.main()