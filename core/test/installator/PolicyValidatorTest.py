import os
import unittest
import tempfile

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.PolicyValidator import PolicyValidator

class PolicyValidatorTest(unittest.TestCase):

    SHARE_DIR = os.path.join(os.path.dirname(__file__),'../../share')
    TEMPLATE_DIR = os.path.join(SHARE_DIR, 'template')

    def setUp(self):
        PolicyValidator.TEMPLATE_CFG = os.path.join(PolicyValidatorTest.TEMPLATE_DIR, os.path.basename(PolicyValidator.TEMPLATE_CFG))
        PolicyValidator.CONFIG = tempfile.mktemp()
        PolicyValidator.CONFIG_SAV = PolicyValidator.CONFIG + '.sav'

    def testConfigurationCreation(self):

        # Simulate the installation of the config file
        open(PolicyValidator.CONFIG, 'w').close()

        self._createConfiguration()

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

        self.assertTrue(os.path.exists(PolicyValidator.CONFIG_SAV))

    def _createConfiguration(self):
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

