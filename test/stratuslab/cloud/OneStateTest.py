import unittest

from stratuslab.cloud.one import OneVmState

class OneStateTest(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass

    def testState(self):
        
        state = OneVmState('0')
        self.assertEquals('Init', str(state))

        state = OneVmState('0','3')
        self.assertEquals('Init', str(state))

    def testLcmState(self):
        
        state = OneVmState('3','0')
        self.assertEquals('Lcm_Init', str(state))

        state = OneVmState('3','16')
        self.assertEquals('Unknown', str(state))

if __name__ == "__main__":
    unittest.main()
        