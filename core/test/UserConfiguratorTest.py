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
import tempfile
import os
from stratuslab.Exceptions import ConfigurationException


class UserConfiguratorTest(unittest.TestCase):
    
    VALID_CONFIG_DEFAULT_ONLY = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>
'''
    
    VALID_CONFIG_DEFAULT_ONLY_WITH_INSTANCE_TYPE = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>
default_instance_type = my.type
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
selected_section = my-section

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
    
    INVALID_CONFIG_NO_SELECTED_SECTION = '''
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
selected_section = my-section-doesnt-exist

[my-section]
endpoint = <another.cloud.frontend.hostname>
username = <another.username>
'''

    VALID_CONFIG_WITH_INSTANCE_TYPES_SECTION = '''
[default]
endpoint = <cloud.frontend.hostname>
username = <username>
password = <password>
default_instance_type = my.type

[instance_types]
alpha = (1, 1, 1)
beta = (2, 2, 2)
bad1 = 44
bad2 = ,
bad3 = 1, 2, 3, 4
bad4 = 
'''
    

    def _createTemporaryFile(self, contents):
        '''user is responsible for deleting the created file'''
        temp = tempfile.NamedTemporaryFile(delete=False)
        try:
            temp.write(contents)
        finally:
            temp.close()
        return temp.name
    
    def testStaticLoader(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        configHolder = UserConfigurator.configFileToDictWithFormattedKeys(file)
        self.assertEqual(configHolder['username'], '<username>')
        self.assertEqual(configHolder['userDefinedInstanceTypes'], {})
    
    def testStaticLoaderWithNamedFile(self):
        file = self._createTemporaryFile(self.VALID_CONFIG_DEFAULT_ONLY)
        try:
            configHolder = UserConfigurator.configFileToDictWithFormattedKeys(file)
        finally:
            os.remove(file)
        self.assertEqual(configHolder['username'], '<username>')
        self.assertEqual(configHolder['userDefinedInstanceTypes'], {})

    def testDefaultInstanceTypeWithoutConfigAttribute(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        usercfg = UserConfigurator(file)
        dict = usercfg.getDict()
        self.assertFalse('default_instance_type' in dict.keys())

    def testDefaultInstanceTypeWithConfigAttribute(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY_WITH_INSTANCE_TYPE)
        usercfg = UserConfigurator(file)
        dict = usercfg.getDict()
        self.assertEqual(dict['default_instance_type'], 'my.type')

    def testUserDefinedInstanceTypes(self):
        file = StringIO.StringIO(self.VALID_CONFIG_WITH_INSTANCE_TYPES_SECTION)
        usercfg = UserConfigurator(file)
        types = usercfg.getUserDefinedInstanceTypes()
        self.assertEqual(len(types.keys()), 2)
        self.assertTrue('alpha' in types.keys())
        self.assertTrue('beta' in types.keys())

    def testStringToTupleConversion(self):
        testValues = { '1,2,3': (1,2,3),
                       '1,,2,,3': (1,2,3),
                       '': (),
                       ',c,c,c': (),
                       '(4,4,4)': (4,4,4),
                       '(0,0,0,0,)': (0,0,0,0),
                       }
        for s in testValues.keys():
            trueValue = testValues[s]
            t = UserConfigurator._instanceTypeStringToTuple(s);
            self.assertEquals(t, trueValue, 'incorrect value mapping: %s, %s, %s' % (s, t, trueValue))

    def testValidTuples(self):
        testValues = [ (1,2,3),
                       (1,1,0),
                       (24,256,1024)
                       ]
        for t in testValues:
            result = UserConfigurator._validInstanceTypeTuple(t);
            self.assertTrue(result, 'valid tuple marked as invalid: %s' % str(t))

    def testInvalidTuples(self):
        testValues = [ (0,1,0),
                       (1,0,0),
                       (),
                       (1,2,3,4),
                       (-1,1,0),
                       (1,-1,0),
                       (1,1,-1),
                       ('a',2,3),
                       (1,'a',3),
                       (1,2,'a')
                       ]
        for t in testValues:
            result = UserConfigurator._validInstanceTypeTuple(t);
            self.assertFalse(result, 'invalid tuple marked as valid: %s' % str(t))

    def testSectionDictWithNoArgument(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        usercfg = UserConfigurator(file)
        values = usercfg.getSectionDict()
        self.assertEquals(len(values), 0)
    
    def testSectionDictWithNonexistentSection(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        usercfg = UserConfigurator(file)
        values = usercfg.getSectionDict('non-existent-section')
        self.assertEquals(len(values), 0)
    
    def testSectionDictWithDefaultSection(self):
        file = StringIO.StringIO(self.VALID_CONFIG_DEFAULT_ONLY)
        usercfg = UserConfigurator(file)
        values = usercfg.getSectionDict('default')
        self.assertEquals(len(values), 3)
        self.assertEquals(values['endpoint'], '<cloud.frontend.hostname>')
        self.assertEquals(values['username'], '<username>')
        self.assertEquals(values['password'], '<password>')
    
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
        file = StringIO.StringIO(self.INVALID_CONFIG_NO_SELECTED_SECTION)
        configurator = UserConfigurator(file)
        self.assertRaises(ConfigurationException, configurator.getDict)

    def testWrongReference(self):
        file = StringIO.StringIO(self.INVALID_CONFIG_WITH_WRONG_REFERENCE)
        configurator = UserConfigurator(file)
        self.assertRaises(ConfigurationException, configurator.getDict)

if __name__ == "__main__":
    unittest.main()
