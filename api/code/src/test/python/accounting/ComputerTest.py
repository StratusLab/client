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

import xml.etree.ElementTree as ET
import unittest

from stratuslab.accounting.Computer import Computer

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
""" % {'1GB' : 1024**3}

class ComputerTest(unittest.TestCase):

    def testComputeTotals(self):
        cmptr = Computer(0, 0, '', True)
        root = ET.fromstring(USAGERECORD_XML)
        cmptr.compute_totals(root)
        
        assert '1' == root.get('total_time')
        assert '1' == root.get('total_cpu')
        assert '1' == root.get('total_ram')
        assert '2' == root.get('total_disk')
        assert '1' == root.get('total_net_rx')
        assert '1' == root.get('total_net_tx')

if __name__ == "__main__":
    unittest.main()
