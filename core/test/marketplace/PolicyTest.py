import unittest
import os
import stratuslab.marketplace.Policy as Policy
from xml.etree.ElementTree import ElementTree
from stratuslab.marketplace.Policy import Policy
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ValidationException, InputException


class PolicyTest(unittest.TestCase):
    def testFilter(self):
        xmltree = ElementTree()
        xmltree2 = ElementTree()
        xmltree.parse(os.path.dirname(__file__) + "/valid-full.xml")
        xmltree2.parse(os.path.dirname(__file__) + "/valid-full2.xml")
        metadataEntries = [xmltree, xmltree2]

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

if __name__ == "__main__":
    unittest.main()
