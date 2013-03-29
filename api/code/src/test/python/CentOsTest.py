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

from stratuslab.system.centos import CentOS

class CentOsTest(unittest.TestCase):

    def testGetBridgeAndIfaceConfigStaticNetwork(self):

        centos = CentOS()

        ifaceConfOrig = """DEVICE=eth0
HWADDR=00:15:17:CF:F1:A0
IPV6INIT=yes
ONBOOT=yes
BOOTPROTO=static
BROADCAST=192.168.1.255
IPADDR=192.168.1.100
NETMASK=255.255.255.0
NETWORK=192.168.1.0
GATEWAY=192.168.1.1
"""
        iface = 'eth0'
        bridge = 'br0'
        
        ifaceConfTest = """DEVICE=eth0
ONBOOT=yes
BRIDGE=br0
IPV6INIT=yes
HWADDR=00:15:17:CF:F1:A0
"""
        bridgeConfTest = """DEVICE=br0
TYPE=Bridge
ONBOOT=yes
DELAY=0
IPV6INIT=yes
BOOTPROTO=static
BROADCAST=192.168.1.255
IPADDR=192.168.1.100
NETMASK=255.255.255.0
NETWORK=192.168.1.0
GATEWAY=192.168.1.1
"""
        bridgeConf, ifaceConf  = centos._buildBridgeAndIfaceConfig(ifaceConfOrig, 
                                                                  iface, bridge)
        assert bridgeConf == bridgeConfTest
        assert ifaceConf == ifaceConfTest

    def testGetBridgeAndIfaceConfigDhcpNetwork(self):

        centos = CentOS()

        ifaceConfOrig = """DEVICE=eth0
HWADDR=00:15:17:CF:F1:A0
IPV6INIT=yes
ONBOOT=yes
BOOTPROTO=dhcp
"""
        iface = 'eth0'
        bridge = 'br0'
        
        ifaceConfTest = """DEVICE=eth0
ONBOOT=yes
BRIDGE=br0
IPV6INIT=yes
HWADDR=00:15:17:CF:F1:A0
"""
        bridgeConfTest = """DEVICE=br0
TYPE=Bridge
ONBOOT=yes
DELAY=0
IPV6INIT=yes
BOOTPROTO=dhcp
"""
        bridgeConf, ifaceConf = centos._buildBridgeAndIfaceConfig(ifaceConfOrig, 
                                                                  iface, bridge)
        assert bridgeConf == bridgeConfTest
        assert ifaceConf == ifaceConfTest
        
if __name__ == "__main__":
    unittest.main()
