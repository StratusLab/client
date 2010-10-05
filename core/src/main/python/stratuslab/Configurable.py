import stratuslab.Util as Util
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printDetail
from stratuslab.Util import printWarning
from stratuslab.Util import printError
from stratuslab.ConfigHolder import ConfigHolder

class Configurable(object):
    def __init__(self, configHolder):
        configHolder.assign(self)
        self.verify()

    @staticmethod
    def convertToSectionDict(config):
        dicts = {}
        for section in config.sections():
            dict = {}
            for k,v in config.items(section):
                dict[k] = v
            dicts[section] = dict
        return dicts

    def parseConfig(self, configFileName):
        return ConfigHolder.parseConfig(configFileName)

    def verify(self):
        pass

    def printAction(self, msg):
        printAction(msg)

    def printStep(self, msg):
        printStep(msg)
    
    def printDetail(self, msg, verboseThreshold=Util.NORMAL_VERBOSE_LEVEL):
        printDetail(msg, self.verboseLevel, verboseThreshold)

    def printWarning(self, msg):
        printWarning(msg)

    def printError(self, msg):
        printError(msg, exit=False)
