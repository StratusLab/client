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
import unittest

import stratuslab.Util as Util
from stratuslab.CloudInfo import CloudInfo

etree = Util.importETree()

class VmInfoTest(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testPopulate(self):
        xml = '''
<root>
    <level1>
        <id1>ID1</id1>
        <level2>
            <level3>
                <id3>ID3</id3>
            </level3>
        </level2>
        <id4>ID4</id4>
    </level1>
</root>
'''
        root = etree.fromstring(xml)

        info = CloudInfo()
        info.populate(root)
        
        self.assertEqual('ID1',info.level1_id1)
        self.assertEqual('ID3',info.level1_level2_level3_id3)
        self.assertEqual('ID4',info.level1_id4)

if __name__ == "__main__":
    unittest.main()
