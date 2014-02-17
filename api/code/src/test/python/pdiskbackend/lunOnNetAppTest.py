import unittest

from stratuslab.pdiskbackend.LUN import LUN
from stratuslab.pdiskbackend.backends.Backend import Backend

class lunOnNetAppTest(unittest.TestCase):

    def setUp(self):
        pass
    def tearDown(self):
        pass

    def testInit(self):
        Backend._type = 'foo'
        LUN('123', proxy=Backend())

if __name__ == "__main__":
    unittest.main()
