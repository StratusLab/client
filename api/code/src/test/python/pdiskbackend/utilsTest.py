import logging
import unittest

from stratuslab.pdiskbackend.utils import initialize_logger
from stratuslab.Exceptions import ConfigurationException

class UtilsTest(unittest.TestCase):

    def setUp(self):
        pass
    def tearDown(self):
        pass

    def test_logger_init(self):
        assert isinstance(initialize_logger('console', 0),
                          logging.Logger)
        assert isinstance(initialize_logger('syslog', 0),
                          logging.Logger)
        self.assertRaises(ConfigurationException, 
                          initialize_logger, *('foo', 0))

if __name__ == "__main__":
    unittest.main()
