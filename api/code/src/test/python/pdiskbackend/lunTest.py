import unittest

from stratuslab.pdiskbackend.LUN import LUN
from stratuslab.pdiskbackend.backends.Backend import Backend

class lunOnNetAppTest(unittest.TestCase):

    def setUp(self):
        Backend._type = 'foo'

    def tearDown(self):
        Backend._type = ''

    def test_init(self):
        LUN('123', proxy=Backend())

    def test_action_not_defined(self):
        lun = LUN('123', proxy=Backend())
        for action in Backend.lun_backend_cmd_mapping.keys():
            # This doesn't work for some reason.
            #self.assertRaises(SystemExit, lun._execute_action(action))
            try:
                lun._execute_action(action)
            except SystemExit:
                pass
            else:
                self.fail('Should have raised SystemExit')

if __name__ == "__main__":
    unittest.main()
