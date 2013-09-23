#!/usr/bin/env python
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique (CNRS)
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

from stratuslab.tm.TMContext import TMContext

class TMContextTest(unittest.TestCase):

    TEST_CONTEXT = '''
  CONTEXT_METHOD="cloud-init"
  CLOUD_INIT_AUTHORIZED_KEYS="DUMMY_DATA"
  CLOUD_INIT_USER_DATA="DUMMY_DATA"   
'''

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testCheckArgs(self):
        self.assertRaises(ValueError, TMContext._checkArgs, None)
        self.assertRaises(ValueError, TMContext._checkArgs, [])
        self.assertRaises(ValueError, TMContext._checkArgs, ['scriptname'])
        self.assertRaises(ValueError, TMContext._checkArgs, ['scriptname', 'dummy context'])

        # should be ok with these fake args
        TMContext._checkArgs(['scriptname', 'context', 'disk'])

    def testParseContextFile(self):
        try:
            _, filename = tempfile.mkstemp()
            with open(filename, 'wb') as f:
                f.write(self.TEST_CONTEXT)
    
            params = TMContext._parseContextFile(filename)

            self.assertEqual(params['context_method'], 'cloud-init')
            self.assertEqual(params['authorized_keys'], 'DUMMY_DATA')
            self.assertEqual(params['user_data'], 'DUMMY_DATA')

        finally:
            os.remove(filename)
        

if __name__ == "__main__":
    unittest.main()
