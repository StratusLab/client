#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
        
