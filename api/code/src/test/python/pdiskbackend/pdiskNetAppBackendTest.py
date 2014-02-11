import unittest

from stratuslab.pdiskbackend.backends.NetAppBackend import getNetAppBackend, NetApp7Mode,\
    NetAppBackend, NetAppCluster
from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder

class BackendTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_getNetAppBackend(self):
        netapp = getNetAppBackend('NetApp', 'proxy', 'mgtUser', 'mgtPrivKey', 
                                  'volume', 'namespace', 'initiatorGroup', 
                                  'snapshotPrefix', ConfigHolder())
        assert isinstance(netapp, NetAppBackend)

        netapp = getNetAppBackend('NetApp-7Mode', 'proxy', 'mgtUser', 'mgtPrivKey', 
                                  'volume', 'namespace', 'initiatorGroup', 
                                  'snapshotPrefix', ConfigHolder())
        assert isinstance(netapp, NetApp7Mode)

        netapp = getNetAppBackend('NetApp-Cluster', 'proxy', 'mgtUser', 'mgtPrivKey', 
                                  'volume', 'namespace', 'initiatorGroup', 
                                  'snapshotPrefix', ConfigHolder())
        assert isinstance(netapp, NetAppCluster)

if __name__ == "__main__":
    unittest.main()
