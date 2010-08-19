from stratuslab.installator.one import OneInstallator
from stratuslab.Util import printAction
from stratuslab.Util import printStep

class Registrar(OneInstallator):

    def __init__(self, options, config):
        self.config = config
        self.deRegister = False
        self.assignAttributes(options)

        self.assignKey(options, config)
        self.assignDrivers(options, config)

    def assignAttributes(self, dictionary):        
        for key, value in dictionary.items():
            setattr(self, key, value)

    def register(self, hostname):
        
        if self.deRegister:
            self._deRegister(hostname)
            return

        self._register(hostname)

    def _deRegister(self, hostname):
        pass

    def _register(self, hostname):
        
        self.nodeAddr = hostname
        printAction('Registering node: %s', hostname)
        self.addCloudNode()
        printAction('Registration successful')
        