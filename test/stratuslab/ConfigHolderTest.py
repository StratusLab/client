import unittest
from stratuslab.ConfigHolder import ConfigHolder

class ConfigHolderTest(unittest.TestCase):


    def testCamelCase(self):
        configHolder = ConfigHolder()
        self.assertEquals('oneTwoThree', configHolder._camelCase('One_Two_Three'))
        self.assertEquals('oneTwoThree', configHolder._camelCase('one_two_three'))
        self.assertEquals('a', configHolder._camelCase('A'))
        self.assertEquals('', configHolder._camelCase(''))

    def testConfigToDict(self):
        configHolder = ConfigHolder()
        config = {'one_two_three': '123'}
        key, value = configHolder._formatConfigKeys(config).items()[0]
        self.assertEquals('oneTwoThree', key)
        self.assertEquals('123', value)


    def testCopy(self):
        original = ConfigHolder({'a':'A'},{'b':'B'})

        copy = original.copy()
        copy.options['a'] = '_A'
        copy.config['b'] = '_B'

        self.assertEquals('A', original.options['a'])
        self.assertEquals('B', original.config['b'])

if __name__ == "__main__":
    unittest.main()