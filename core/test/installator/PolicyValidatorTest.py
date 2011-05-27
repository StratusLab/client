import os
import unittest
import tempfile

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.PolicyValidator import PolicyValidator

class PolicyValidatorTest(unittest.TestCase):

    SHARE_DIR = '../../share'
    TEMPLATE_DIR = os.path.join(SHARE_DIR, 'template')

    def testConfigurationCreation(self):
        PolicyValidator.TEMPLATE_CFG = os.path.join(PolicyValidatorTest.TEMPLATE_DIR, os.path.basename(PolicyValidator.TEMPLATE_CFG))
        PolicyValidator.CONFIG = tempfile.mktemp()

        configHolder = ConfigHolder(config={
                                    'validate_metadata': True,
                                    'whitelistendorsers': 'whitelistendorsersv1, whitelistendorsersv2',
                                    'whitelistimages': 'whitelistimagesv1, whitelistimagesv2',
                                    'blacklistimages': 'blacklistimagesv1, blacklistimagesv2',
                                    'blacklistendorsers': 'blacklistendorsersv1, blacklistendorsersv2',
                                    'blacklistchecksums': 'blacklistchecksumsv1, blacklistchecksumsv2',
                                    })
        policyValidator = PolicyValidator(configHolder)
        policyValidator.run()

        policyCfg = ConfigHolder.parseConfig(PolicyValidator.CONFIG)
        
        sectionName = 'validatemetadatafile'
        self.assertEquals('True', policyCfg.get(sectionName, 'activate'))

        sectionNames = ('whitelistendorsers', 
                        'whitelistimages', 
                        'blacklistimages', 
                        'blacklistendorsers', 
                        'blacklistchecksums')
        for sectionName in sectionNames:
            self.assertEquals('%(section)sv1, %(section)sv2' % {'section': sectionName}, 
                              policyCfg.get(sectionName, 'group1'))

if __name__ == "__main__":
    unittest.main()

