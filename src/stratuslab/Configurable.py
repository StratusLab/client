import Util
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printDetail

class Configurable(object):
    def __init__(self, configHolder):
        configHolder.assign(self)

    def printAction(self, msg):
        printAction(msg)

    def printStep(self, msg):
        printStep(msg)
    
    def printDetail(self, msg, verboseThreshold=Util.NORMAL_VERBOSE_LEVEL):
        printDetail(msg, self.verboseLevel, verboseThreshold)
