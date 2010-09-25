import Util
from stratuslab.Configurator import Configurator

class ConfigHolder(object):
    
    def __init__(self, options={}, config={}):
        self.options = options
        self.config = config

    def assign(self, obj):
        Util.assignAttributes(obj, Configurator.formatConfigKeys(self.config))
        Util.assignAttributes(obj, self.options)
