import os
import shutil
from Configurable import Configurable
from Exceptions import ConfigurationException

class Configurator(Configurable):

    @staticmethod
    def assignConfigAttributes(instance, config):
        for key, value in config.items():
            setattr(instance, Configurator._camelCase(key), value)
        return instance
 
    @staticmethod
    def formatConfigKeys(config):
        dict = {}
        for k, v in config.items():
            dict[Configurator._camelCase(k)] = v
        return dict

    @staticmethod
    def _camelCase(key):
        formattedKey = ''.join([part.title() for part in key.split('_')])
        if len(formattedKey) > 0:
            formattedKey = formattedKey[0].lower() + formattedKey[1:]
        return formattedKey

    def __init__(self, configHolder):
        super(Configurator, self).__init__(configHolder)
        
        self.baseConfigFile = self.configFile + '.ref'
        self.config = None
        self.baseConfig = None
        self._load()

    def _load(self):
        self.printDetail('Loading configuration file %s' % self.baseConfigFile)
        self.baseConfig = Configurable.parseConfig(self.baseConfigFile)
        self._createConfigIfRequired()        
        self.printDetail('Loading configuration file %s' % self.configFile)
        self.config = Configurable.parseConfig(self.configFile)

    def _createConfigIfRequired(self):
        if not os.path.isfile(self.configFile):
            self.printDetail('Creating user configuration file %s' % self.configFile)
            shutil.copy(self.baseConfigFile, self.configFile)

    def getValue(self, key):
        section, _ = self._findSectionAndValue(key, self.config)
        return self.config.get(section, key) 

    def displayDefaultKeys(self):
        columnSize = 25
        defaultConfig = Configurable.convertToSectionDict(Configurable.parseConfig(self.baseConfigFile))

        width = columnSize * 3 + 1
        line = '-' * width
        doubleLine = '=' * width
        startEmphasis = '\033[1;31m'
        stopEmphasis = '\033[0m'
        print '\n', doubleLine
        print ' %(startEmphasis)s%(section)s%(stopEmphasis)s' % (
                                 {'section': 'Section'.center(width),
                                  'startEmphasis': startEmphasis, 'stopEmphasis': stopEmphasis})
        print line
        print ' %(startEmphasis)s%(first)s%(stopEmphasis)s|  %(startEmphasis)s%(second)s%(stopEmphasis)s|  %(startEmphasis)s%(third)s%(stopEmphasis)s' % (
                                 {'first': 'Config key'.ljust(columnSize),
                                  'second': 'Current value'.ljust(columnSize),
                                  'third': 'Default value', 
                                  'startEmphasis': startEmphasis, 'stopEmphasis': stopEmphasis})
        first = True

        for section in defaultConfig.keys():
            if first:
                print doubleLine
            else:
                print line
            first = False
            print '\033[1;31m%s\033[0m'.center(width) % section
            print line
            for key in defaultConfig[section]:
                print ' %s|  %s|  %s' % (
                                         key.ljust(columnSize),
                                         self.getValue(key).ljust(columnSize),
                                         defaultConfig[section].get(key))

    def _convertToDict(self, config):
        dict = {}
        for section in config.sections():
            for k,v in config.items(section):
                dict[k] = v
        return dict

    def setOption(self, key, value):
        section, _ = self._findSectionAndValue(key, self.config)
        self.config.set(section, key, value) 
        self.writeUserConfig()

    def _findSectionAndValue(self, key, config):
        section = None
        value = None
        for s in config.sections():
            for k, v in config.items(s):
                if k == key:
                    section = s
                    value = v 
                    break
            if section:
                break
        if not section:
            raise ConfigurationException('Key %s does not exist' % key)
        return section, value

    def writeUserConfig(self):
        fd = open(self.configFile, 'wb')
        self.config.write(fd)
        fd.close()

    def revertConfig(self):
        if os.path.isfile(self.userConfigFile):
            os.remove(self.userConfigFile)