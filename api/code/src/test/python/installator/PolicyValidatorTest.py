import os
import unittest
import tempfile

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.PolicyValidator import PolicyValidator

class PolicyValidatorTest(unittest.TestCase):

    SHARE_DIR = os.path.join(os.path.dirname(__file__),'../../share')
    TEMPLATE_DIR = os.path.join(SHARE_DIR, 'template')

    def setUp(self):
        PolicyValidator.CONFIG = tempfile.mktemp()
        PolicyValidator.CONFIG_SAV = PolicyValidator.CONFIG + '.sav'

    def testConfigurationCreation(self):

        # Simulate the installation of the config file
        open(PolicyValidator.CONFIG, 'w').close()

        self._createConfiguration()

        policyCfg = ConfigHolder.parseConfig(PolicyValidator.CONFIG)
        
        sectionNames = ('endorsers', 
                        'images', 
                        'checksums')

        for sectionName in sectionNames:
            self.assertEquals('whitelist%(section)sv1, whitelist%(section)sv2' % {'section': sectionName}, 
                              policyCfg.get(sectionName, 'whitelist' + sectionName))
            self.assertEquals('blacklist%(section)sv1, blacklist%(section)sv2' % {'section': sectionName}, 
                              policyCfg.get(sectionName, 'blacklist' + sectionName))

        self.assertTrue(os.path.exists(PolicyValidator.CONFIG_SAV))

    def _createConfiguration(self):
        configHolder = ConfigHolder(config={
                                    'whitelistendorsers': 'whitelistendorsersv1, whitelistendorsersv2',
                                    'whitelistimages': 'whitelistimagesv1, whitelistimagesv2',
                                    'whitelistchecksums': 'whitelistchecksumsv1, whitelistchecksumsv2',
                                    'blacklistimages': 'blacklistimagesv1, blacklistimagesv2',
                                    'blacklistendorsers': 'blacklistendorsersv1, blacklistendorsersv2',
                                    'blacklistchecksums': 'blacklistchecksumsv1, blacklistchecksumsv2',
                                    })
        policyValidator = PolicyValidator(configHolder)
        policyValidator._setupFrontend()

    
    def testConfigurationCreationSkippedIfBackupFileExists(self):

        open(PolicyValidator.CONFIG_SAV, 'w').close()
        open(PolicyValidator.CONFIG, 'w').close()

        self._createConfiguration()

        # Should be empty, since not created        
        self.assertEquals(open(PolicyValidator.CONFIG).read(), '')


    def testReplacedOnlyIfBackupFileDoesntExist(self):
        
        policyValidator = PolicyValidator()
        self.assertFalse(policyValidator._backupConfigFileExists(), 'File %s doesn\'t exist, should be False' % os.path.splitext(PolicyValidator.CONFIG_SAV)[1])

        open(PolicyValidator.CONFIG_SAV, 'w').close()
        self.assertTrue(policyValidator._backupConfigFileExists(), 'File %s exists, should be True' % os.path.splitext(PolicyValidator.CONFIG_SAV)[1])

        

if __name__ == "__main__":
    unittest.main()

