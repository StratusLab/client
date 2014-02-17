import os
import tempfile
import unittest

from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder
from stratuslab.pdiskbackend import defaults

class BackendTest(unittest.TestCase):

    def setUp(self):
        fd, self.cfg_fname = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        os.unlink(self.cfg_fname)

    def testInit(self):
        ch = ConfigHolder(self.cfg_fname)
        assert defaults.CONFIG_LOG_DIRECTION == ch.get(defaults.CONFIG_MAIN_SECTION, 'log_direction')
        
    def testConfigFileDoesNotExist(self):
        self.assertRaises(SystemExit, 
                          ConfigHolder, **{'config_file_name':'/foo/bar'})       

if __name__ == "__main__":
    unittest.main()
