import os

import stratuslab.Util as Util
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printDetail
from stratuslab.Util import printError
from ConfigParser import SafeConfigParser
from Exceptions import ConfigurationException

class Configurable(object):
    def __init__(self, configHolder):
        configHolder.assign(self)
        self.verify()

    @staticmethod
    def configFileToDict(configFileName):
        config = Configurable.parseConfig(configFileName)
        dict = Configurable.convertToDict(config)
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
    def convertToDict(config):
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

    def verify(self):
        pass

    def printAction(self, msg):
        printAction(msg)

    def printStep(self, msg):
        printStep(msg)
    
    def printDetail(self, msg, verboseThreshold=Util.NORMAL_VERBOSE_LEVEL):
        printDetail(msg, self.verboseLevel, verboseThreshold)

    def printError(self, msg):
        printError(msg, exit=False)
