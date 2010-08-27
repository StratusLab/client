import os
import shutil
from ConfigParser import SafeConfigParser
from Util import defaultConfigSection
from Util import parseConfig
from Util import validateConfig

class Configurator(object):

    def __init__(self, configFile):
        self.baseConfigFile = configFile
        
        if not os.path.isfile(self.baseConfigFile):
            raise ValueError('Base configuration file does not exist')

        self.baseConfig = SafeConfigParser()
        self.baseConfig.read(configFile)    
        validateConfig(self.baseConfig)

        self._buildUserConfig()

    def getValue(self, key):
        if not self.userConfig.has_option(defaultConfigSection, key):
            raise ValueError('Specified key "%s" does not exist' % key)

        return self.userConfig.get(defaultConfigSection, key) 

    def _buildUserConfig(self):
        self.userConfigFile = self.baseConfigFile.replace('.ref', '')
        
        if not os.path.isfile(self.userConfigFile):
            shutil.copy(self.baseConfigFile, self.userConfigFile)

        self.userConfig = SafeConfigParser()
        self.userConfig.read(self.userConfigFile)
        validateConfig(self.userConfig)

    def displayDefaultKeys(self):
        columnSize = 25
        defaultConfig = parseConfig(self.baseConfigFile)
        userConfig = parseConfig(self.userConfigFile)

        print ' %s|  %s|  %s' % (
                                 'Config key'.ljust(columnSize),
                                 'Current value'.ljust(columnSize),
                                 'Default value')
        print '-' * (columnSize * 3 + 1)

        for key in defaultConfig.keys():
            print ' %s|  %s|  %s' % (
                                     key.ljust(columnSize),
                                     userConfig.get(key).ljust(columnSize),
                                     defaultConfig.get(key))

    def setOption(self, key, value):
        if not self.userConfig.has_option(defaultConfigSection, key):
            raise ValueError('Specified key does not exist')

        self.userConfig.set(defaultConfigSection, key, value) 
        self.writeUserConfig()

    def writeUserConfig(self):
        fd = open(self.userConfigFile, 'wb')
        self.userConfig.write(fd)
        fd.close()

    def revertConfig(self):
        if os.path.isfile(self.userConfigFile):
            os.remove(self.userConfigFile)

