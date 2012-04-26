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
import unittest
from ConfigParser import SafeConfigParser

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.ConfigHolder import UserConfigurator
from stratuslab import Util
import StringIO
from stratuslab.Exceptions import ConfigurationException


class UserConfiguratorTest(unittest.TestCase):
    
    VALID_CONFIG_DEFAULT_ONLY = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>
'''
    
    VALID_CONFIG_WITH_SECTION = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>

[my-section]
endpoint = <another.cloud.frontend.hostname>
username = <another.username>

[my-other-section]
endpoint = <yet.another.cloud.frontend.hostname>
username = <yet.another.username>
'''

    VALID_CONFIG_WITH_SECTION_AND_REFERENCE = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>
default_section = my-section

[my-section]
endpoint = <another.cloud.frontend.hostname>
username = <another.username>

[my-other-section]
endpoint = <yet.another.cloud.frontend.hostname>
username = <yet.another.username>
'''

    INVALID_CONFIG_NO_VALUE = '''
[default]
endpoint
'''
    
    INVALID_CONFIG_NO_DEFAULT_SECTION = '''
[nodefault]
endpoint = <nodefault.cloud.frontend.hostname>
username = <username>
password = <password>
'''

    INVALID_CONFIG_WITH_WRONG_REFERENCE = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>
default_section = my-section-doesnt-exist

[my-section]
endpoint = <another.cloud.frontend.hostname>
username = <another.username>
'''
    
    def testDefaultOnly(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        configurator = UserConfigurator(file)
        dict = configurator.getDict()
        self.assertEqual(dict['username'], '<username>')
        
    def testWithSection(self):
        file = StringIO.StringIO(self.VALID_CONFIG_WITH_SECTION)
        configurator = UserConfigurator(file)
        dict = configurator.getDict()
        self.assertEqual(dict['username'], '<username>')

        dict = configurator.getDict("my-section")        
        self.assertEqual(dict['username'], '<another.username>')
        
    def testWrongSection(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        configurator = UserConfigurator(file)
        self.assertRaises(ConfigurationException, configurator.getDict, "my-section-doesnt-exist")        

    def testWithSectionAndReference(self):
        file = StringIO.StringIO(self.VALID_CONFIG_WITH_SECTION_AND_REFERENCE)
        configurator = UserConfigurator(file)
        dict = configurator.getDict()
        self.assertEqual(dict['username'], '<another.username>')

    def testMissingValue(self):
        file = StringIO.StringIO(self.INVALID_CONFIG_NO_VALUE)
        self.assertRaises(ConfigurationException, UserConfigurator, file)

    def testMissingDefaultSection(self):
        file = StringIO.StringIO(self.INVALID_CONFIG_NO_DEFAULT_SECTION)
        configurator = UserConfigurator(file)
        self.assertRaises(ConfigurationException, configurator.getDict)

    def testWrongReference(self):
        file = StringIO.StringIO(self.INVALID_CONFIG_WITH_WRONG_REFERENCE)
        configurator = UserConfigurator(file)
        self.assertRaises(ConfigurationException, configurator.getDict)

if __name__ == "__main__":
    unittest.main()
