from stratuslab.installator.one import OneInstallator
from stratuslab.Util import assignAttributes
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Monitor import Monitor
from stratuslab.Exceptions import InputException

class Registrar(OneInstallator):

    def __init__(self, options, config):
        self.config = config
        self.deRegister = False
        assignAttributes(self, options)
        
        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))        
        self.cloud.setCredentials('oneadmin', self.password)

        self.assignDrivers(self, config)

    def register(self, hostnames):
        
        id = None
        for hostname in hostnames:
            if self.deRegister:
                self.deregister(hostname)
            else:
                id = self._register(hostname)
        return id

    def deregister(self, hostname):
        try:
            id = int(hostname)
        except:
            id = self._getHostnameId(hostname)
        self.removeCloudNode(id)

    def _getHostnameId(self, hostname):
        monitor = Monitor(self.__dict__, self.config)
        infoList = monitor.list()
        info = None
        for i in infoList:
            if i.name == hostname:
                info = i
                break
        if not info:
            raise InputException('Failed to find node with hostname %s' % hostname)
        return int(info.id)
        

    def _register(self, hostname):
        
        self.nodeAddr = hostname
        return self.addCloudNode()
        