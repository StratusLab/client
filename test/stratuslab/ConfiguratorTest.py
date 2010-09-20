import unittest
from stratuslab.Configurator import Configurator

class ConfiguratorTest(unittest.TestCase):

    def testCamelCase(self):
        self.assertEquals('oneTwoThree', Configurator._camelCase('One_Two_Three'))
        self.assertEquals('oneTwoThree', Configurator._camelCase('one_two_three'))
        self.assertEquals('a', Configurator._camelCase('A'))
        self.assertEquals('', Configurator._camelCase(''))

    def testConfigToDict(self):
        config = {'one_two_three': '123'}
        key, value = Configurator.formatConfigKeys(config).items()[0]
        self.assertEquals('oneTwoThree', key)
        self.assertEquals('123', value)

if __name__ == "__main__":
    unittest.main()