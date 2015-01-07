import os
import unittest
import tempfile
from mock import Mock

from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder
from stratuslab.pdiskbackend.PdiskBackendProxyFactory import PdiskBackendProxyFactory
from stratuslab.pdiskbackend.backends.NetAppBackend import NetAppBackend
from stratuslab.pdiskbackend.backends.CephBackend import CephBackend
from stratuslab.pdiskbackend.backends.FileBackend import FileBackend
from stratuslab.pdiskbackend.backends.LVMBackend import LVMBackend

CONFIG_TEST = """
[main]
mgt_user_name = root
mgt_user_private_key = /some/file.rsa

[foo]
type = bar

[netapp.com]
type = NetApp
[7mode.netapp.com]
type = NetApp-7Mode
[cluster.netapp.com]
type = NetApp-cluster

[ceph.org]
type = Ceph

[file.org]
type = File

[lvm.org]
type = LVM
"""

class BackendTest(unittest.TestCase):

    def setUp(self):
        fd, self.cfg_fname = tempfile.mkstemp()
        os.write(fd, CONFIG_TEST)
        os.close(fd)

    def tearDown(self):
        os.unlink(self.cfg_fname)

    def testInit(self):
        ch = ConfigHolder(self.cfg_fname)
        ch.get_proxy_name = Mock(return_value='foo')
        self.assertRaises(SystemExit,
                          PdiskBackendProxyFactory.createBackendProxy, ch)

    def testCreateBackends(self):
        ch = ConfigHolder(self.cfg_fname)
        ch._set_backend_proxy_specific_attributes = Mock()

        for netapp_type in ['netapp.com', '7mode.netapp.com', 'cluster.netapp.com']:
            ch.get_proxy_name = Mock(return_value=netapp_type)
            assert isinstance(PdiskBackendProxyFactory.createBackendProxy(ch),
                              NetAppBackend)

        ch.get_proxy_name = Mock(return_value='ceph.org')
        assert isinstance(PdiskBackendProxyFactory.createBackendProxy(ch),
                          CephBackend)

        ch.get_proxy_name = Mock(return_value='file.org')
        assert isinstance(PdiskBackendProxyFactory.createBackendProxy(ch),
                          FileBackend)

        ch.get_proxy_name = Mock(return_value='lvm.org')
        assert isinstance(PdiskBackendProxyFactory.createBackendProxy(ch),
                          LVMBackend)

if __name__ == "__main__":
    unittest.main()
