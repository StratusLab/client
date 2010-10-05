import os
from ConfigParser import SafeConfigParser

import Util
from Exceptions import ConfigurationException

class ConfigHolder(object):
    
    @staticmethod
    def configFileToDict(configFileName):
        config = ConfigHolder.parseConfig(configFileName)
        dict = ConfigHolder._convertToDict(config)
        return dict
        
    @staticmethod
    def convertToSectionDict(config):
        dicts = {}
        for section in config.sections():
            dict = {}
            for k,v in config.items(section):
                dict[k] = v
            dicts[section] = dict
        return dicts

    @staticmethod
    def _convertToDict(config):
        dict = {}
        for section in config.sections():
            for k,v in config.items(section):
                dict[k] = v
        return dict

    @staticmethod
    def parseConfig(configFileName):
        if not os.path.isfile(configFileName):
            msg = 'Configuration file %s does not exist' % configFileName
            raise ConfigurationException(msg)
        config = SafeConfigParser()
        config.read(configFileName)
        return config

    def __init__(self, options={}, config={}):
        self.options = options
        self.config = config

    def assign(self, obj):
        Util.assignAttributes(obj, self._formatConfigKeys(self.config))
        Util.assignAttributes(obj, self.options)

    def _formatConfigKeys(self, config):
        dict = {}
        for k, v in config.items():
            dict[self._camelCase(k)] = v
        return dict

    def _camelCase(self, key):
        formattedKey = ''.join([part.title() for part in key.split('_')])
        if len(formattedKey) > 0:
            formattedKey = formattedKey[0].lower() + formattedKey[1:]
        return formattedKey


