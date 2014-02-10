import unittest

from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder
from stratuslab.pdiskbackend import defaults

class BackendTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testInit(self):
        ch = ConfigHolder()
        assert defaults.LOG_FILE == ch.get(defaults.CONFIG_MAIN_SECTION, 'log_file')
        
    def testConfigFileDoesNotExist(self):
        self.assertRaises(SystemExit, 
                          ConfigHolder, **{'config_file_name':'/foo/bar'})       

if __name__ == "__main__":
    unittest.main()
