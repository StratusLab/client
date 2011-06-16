import unittest
import os
from xml.etree.ElementTree import ElementTree
from stratuslab.marketplace.Policy import Policy
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ValidationException

class PolicyTest(unittest.TestCase):
    
    def testFilter(self):
        xmltree = ElementTree()
        xmltree.parse(os.path.dirname(__file__) + "/valid-full.xml")
        
        metadataEntries = xmltree.findall('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
        configHolder = ConfigHolder()
        policy = Policy(os.path.dirname(__file__) + "/policy.cfg", configHolder)
        filtered1 = policy._filter(metadataEntries, policy.whiteListEndorsers)
        if len(filtered1) == 0:
                raise ValidationException('Failed policy check')
        print len(filtered1)

        filtered2 = policy._filter(filtered1, policy.blackListChecksums)
        if len(filtered2) == 0:
                raise ValidationException('Failed policy check')
        print len(filtered2)

    def testActivate(self):
        policy = Policy(os.path.dirname(__file__) + "/policy.cfg")
        policy.validateMetaData = ['no']
        self.assertFalse(policy._isActive())
        policy.validateMetaData = ['yes']
        self.assertTrue(policy._isActive())


if __name__ == "__main__":
    unittest.main()
