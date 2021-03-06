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
from stratuslab.ConfigHolder import ConfigHolder

class ConfigHolderTest(unittest.TestCase):


    def testCamelCase(self):
        configHolder = ConfigHolder()
        self.assertEqual('oneTwoThree', configHolder._camelCase('One_Two_Three'))
        self.assertEqual('oneTwoThree', configHolder._camelCase('one_two_three'))
        self.assertEqual('a', configHolder._camelCase('a'))
        self.assertEqual('', configHolder._camelCase(''))

    def testConfigToDict(self):
        configHolder = ConfigHolder()
        config = {'one_two_three': '123'}
        key, value = configHolder._formatConfigKeys(config).items()[0]
        self.assertEqual('oneTwoThree', key)
        self.assertEqual('123', value)

    def testCopy(self):
        original = ConfigHolder({'a':'A'},{'b':'B'})

        copy = original.copy()
        copy.options['a'] = '_A'
        copy.config['b'] = '_B'

        self.assertEqual('A', original.options['a'])
        self.assertEqual('B', original.config['b'])

    def testToString(self):
        configHolder = ConfigHolder({'a':'A'},{'b':'B'})
        result = """* ConfigHolder:
** OPTIONS:
  a = A
** CONFIG:
  b = B
"""
        self.assertEqual(str(configHolder), result)

    def testGetterSetter(self):
        configHolder = ConfigHolder({'a':'A'},{'b':'B'})

        configHolder.c = 'C'

        self.assertEqual('A', configHolder.a)
        self.assertEqual('B', configHolder.b)

        self.assertEqual('C', configHolder.c)
        
    def testGetterSetterEmpty(self):
        configHolder = ConfigHolder()

        try:
            configHolder.a
        except AttributeError:
            pass
        else:
            self.fail()
        
    def testGetterSetterEmpty2(self):
        self.assertRaises(TypeError, ConfigHolder, None, None)


if __name__ == "__main__":
    unittest.main()
