import unittest
import os
from xml.etree.ElementTree import ElementTree
from stratuslab.marketplace.Policy import Policy
from mock.mock import Mock
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader

class PolicyTest(unittest.TestCase):
    
    def testFilterWithTwoEntriesOnlyOneValid(self):
        xml = ElementTree()
        xml.parse(os.path.dirname(__file__) + "/valid-multiple-entries.xml")
        
        manifests = ManifestDownloader()._extractManifestInfos(xml)

        Policy.POLICY_CFG = os.path.dirname(__file__) + "/policy.cfg"
        policy = Policy()
        policy._downloadManifests = Mock(return_value=manifests)

        filteredManifestList = policy.check(manifests[0].identifier)

        self.assertEqual(1, len(filteredManifestList))

    def testFilterWithOneEntryAndValid(self):
        xml = ElementTree()
        xml.parse(os.path.dirname(__file__) + "/valid-single-entry.xml")
        
        manifests = ManifestDownloader()._extractManifestInfos(xml)

        Policy.POLICY_CFG = os.path.dirname(__file__) + "/policy.cfg"
        policy = Policy()
        policy._downloadManifests = Mock(return_value=manifests)

        filteredManifestList = policy.check(manifests[0].identifier)

        self.assertEqual(1, len(filteredManifestList))

if __name__ == "__main__":
    unittest.main()
