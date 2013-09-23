#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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
import tempfile
import unittest

import stratuslab.controller.util as util

from ConfigParser import SafeConfigParser


class UtilTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testDefaultsFromEmptyCfg(self):
        _, cfg_file = tempfile.mkstemp()

        params = util.read_cb_cfg('pdc', cfg_file)

        os.remove(cfg_file)
        self.assertEquals('localhost:8091', params['host'])
        self.assertEquals('default', params['bucket'])
        self.assertEquals('', params['password'])
        self.assertIsNone(params['docid'])

    def testCfgValuesFromDefaultSection(self):
        cfg_parser = SafeConfigParser()

        cfg_parser.set('DEFAULT', 'host', 'myhost:9999')
        cfg_parser.set('DEFAULT', 'bucket', 'mybucket')
        cfg_parser.set('DEFAULT', 'password', 'mypassword')
        cfg_parser.set('DEFAULT', 'docid', 'mydocid')

        _, cfg_file = tempfile.mkstemp()
        with open(cfg_file, 'w') as fp:
            cfg_parser.write(fp)

        params = util.read_cb_cfg('pdc', cfg_file)

        os.remove(cfg_file)
        self.assertEquals('myhost:9999', params['host'])
        self.assertEquals('mybucket', params['bucket'])
        self.assertEquals('mypassword', params['password'])
        self.assertEquals('mydocid', params['docid'])

    def testCfgValuesFromNamedSection(self):
        cfg_parser = SafeConfigParser()

        cfg_parser.set('DEFAULT', 'host', 'myhost:9999')
        cfg_parser.set('DEFAULT', 'bucket', 'mybucket')
        cfg_parser.set('DEFAULT', 'password', 'mypassword')
        cfg_parser.set('DEFAULT', 'docid', 'mydocid')

        cfg_parser.add_section('pdc')
        cfg_parser.set('pdc', 'host', 'pdchost:9999')
        cfg_parser.set('pdc', 'bucket', 'pdcbucket')
        cfg_parser.set('pdc', 'password', 'pdcpassword')
        cfg_parser.set('pdc', 'docid', 'pdcdocid')

        _, cfg_file = tempfile.mkstemp()
        with open(cfg_file, 'w') as fp:
            cfg_parser.write(fp)

        params = util.read_cb_cfg('pdc', cfg_file)

        os.remove(cfg_file)
        self.assertEquals('pdchost:9999', params['host'])
        self.assertEquals('pdcbucket', params['bucket'])
        self.assertEquals('pdcpassword', params['password'])
        self.assertEquals('pdcdocid', params['docid'])

if __name__ == "__main__":
    unittest.main()
