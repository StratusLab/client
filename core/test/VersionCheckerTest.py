#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
import sys
import unittest

from stratuslab.VersionChecker import VersionChecker

class VersionCheckTest(unittest.TestCase):

    MIN_SAVE = ()
    VERSION_INFO_SAVE = ()

    def setUp(self):
        VERSION_INFO_SAVE = sys.version_info
        sys.version_info = (2, 6, 5, 'final', 0)
        VersionCheckTest.MIN_SAVE = VersionChecker.MINIMUM_VERSION

    def tearDown(self):
        sys.version_info = VersionCheckTest.VERSION_INFO_SAVE
        VersionChecker.MINIMUM_VERSION = VersionCheckTest.MIN_SAVE

    def testGoodVersions(self):

        VersionChecker().check()

        VersionChecker.MINIMUM_VERSION = (2, 5)
        VersionChecker().check()
    
    def testBadVersions(self):
        min = VersionChecker.MINIMUM_VERSION
        VersionChecker.MINIMUM_VERSION = (3, 6)
        
        try:
            VersionChecker().check()
        except:
            pass
        else:
            self.fail('should have raised')
    
    
    
if __name__ == "__main__":
    unittest.main()
