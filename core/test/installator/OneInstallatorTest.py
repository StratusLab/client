import unittest

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.OpenNebulaFrontend import OpenNebulaFrontend

class OneInstallatorTest(unittest.TestCase):

    VNET_INFO_XML = """
<VNET>
  <ID>%s</ID>
  <UID>0</UID>
  <GID>0</GID>
  <UNAME>oneadmin</UNAME>
  <GNAME>oneadmin</GNAME>
  <NAME>%s</NAME>
  <TYPE>1</TYPE>
  <BRIDGE>br0</BRIDGE>
  <PUBLIC>1</PUBLIC>
  <TOTAL_LEASES>2</TOTAL_LEASES>
  <TEMPLATE>
    <BRIDGE><![CDATA[br0]]></BRIDGE>
    <LEASES>
      <IP><![CDATA[62.217.120.178]]></IP>
      <MAC><![CDATA[00:16:3e:d9:78:b2]]></MAC>
    </LEASES>
    <NAME><![CDATA[public]]></NAME>
    <TYPE><![CDATA[FIXED]]></TYPE>
  </TEMPLATE>
  <LEASES>
    <LEASE>
      <IP>62.217.120.178</IP>
      <MAC>00:16:3e:d9:78:b2</MAC>
      <USED>0</USED>
      <VID>-1</VID>
    </LEASE>
  </LEASES>
</VNET>
"""

    def test_getNetworkIdsFromNetworkNames(self):
        ch = ConfigHolder()
        ch.set('frontendSystem', 'fedora')
        ch.set('oneHome', '~')
        ch.set('oneUsername', 'foo')
        ch.set('onePassword', 'bar')
        oi = OpenNebulaFrontend(ch)
        def _getVnetInfoXml(vnet_name):
            if vnet_name == 'public':
                xml = OneInstallatorTest.VNET_INFO_XML % ('0', vnet_name)
            elif vnet_name == 'local':
                xml = OneInstallatorTest.VNET_INFO_XML % ('1', vnet_name)
            elif vnet_name == 'private':
                xml = OneInstallatorTest.VNET_INFO_XML % ('2', vnet_name)
            return xml
        oi._getVnetInfoXml = _getVnetInfoXml

        ids = oi._getVnetIdsFromVnetNames()
        assert [0, 1, 2] == ids

if __name__ == "__main__":
    unittest.main()
