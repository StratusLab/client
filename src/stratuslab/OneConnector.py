import xmlrpclib
from stratuslab.Util import shaHexDigest

class OneConnector(object):
    _sessionString = None
    
    def __init__(self, server):
        self.server = server
        self.rpc = xmlrpclib.ServerProxy(server)
    
    def setCredentials(self, username, password):
        self._sessionString = '%s:%s' % (username, shaHexDigest(password))
        
    def startVm(self, vmTpl):
        ret, vmId = self.rpc.one.vm.allocate(self._sessionString, vmTpl)
        
        if not ret:
            raise Exception(vmId)
        else:
            return vmId
        
    def actionOnVm(self, vmId, action):
        ret, err = self.rpc.one.vm.action(self._sessionString, vmId, action)
        
        if not ret:
            raise Exception(err)
        
    def getVmInfo(self, vmId):
        ret, info = self.rpc.one.vm.info(self._sessionString, vmId)
        
        if not ret:
            raise Exception(info)
        else:
            return info
        
    def getVmState(self, vmId):
        info = self.getVmInfo(vmId)
        print info
        return 'pending'
        