# -*- coding: utf-8 -*-
import os
from ConfigParser import SafeConfigParser

from stratuslab.Util import defaultConfigSection, validConfiguration


class Configurator(object):

    def __init__(self, configFile):
        self.baseConfigFile = configFile
        if not os.path.isfile(self.baseConfigFile):
            raise ValueError('Base configuration file does not exist')

        self.baseConfig = SafeConfigParser()
        self.baseConfig.read(configFile)    
        validConfiguration(self.baseConfig)

        self._buildUserConfig()

    def _buildUserConfig(self):
        self.userConfigFile = '%s.user' % self.baseConfigFile
        
        if os.path.isfile(self.userConfigFile):
            self.userConfig = SafeConfigParser()
            self.userConfig.read(self.userConfigFile)
            validConfiguration(self.userConfig)
        else:
            self.userConfig = self.baseConfig

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

