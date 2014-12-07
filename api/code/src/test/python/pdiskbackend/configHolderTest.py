import os
import tempfile
import unittest

from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder
from stratuslab.pdiskbackend import defaults

CONFIG_TEST = """
[main]
iscsi_proxies = foo,bar,baz

[baz]
baz_one = abc
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
        assert defaults.CONFIG_LOG_DIRECTION == ch.get(defaults.CONFIG_MAIN_SECTION, 'log_direction')

    def testConfigFileDoesNotExist(self):
        self.assertRaises(SystemExit,
                          ConfigHolder, **{'config_file_name':'/foo/bar'})

    def test_force_iscsi_proxy(self):
        ch = ConfigHolder(self.cfg_fname)

        assert 3 == len(ch.get_proxy_names())
        assert 'foo' == ch.get_proxy_name()

        self.assertRaises(SystemExit,
                          ch.force_iscsi_proxy, ('bar',))

        ch.force_iscsi_proxy('baz')
        assert 'baz' == ch.get_proxy_name()


if __name__ == "__main__":
    unittest.main()
