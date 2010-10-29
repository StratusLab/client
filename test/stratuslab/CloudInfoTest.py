#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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

try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise Exception("Failed to import ElementTree from any known place")

from stratuslab.CloudInfo import CloudInfo

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
    </level1>
</root>
'''
        root = etree.fromstring(xml)

        info = CloudInfo()
        info.populate(root)
        
        self.assertEqual('ID1',info.id1)
        self.assertEqual('ID3',info.id3)

if __name__ == "__main__":
    unittest.main()
