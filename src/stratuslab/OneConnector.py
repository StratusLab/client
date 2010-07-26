import xmlrpclib
from stratuslab.Util import shaHexDigest, filePutContents
from xml.etree.ElementTree import ElementTree

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
        res = self.rpc.one.vm.action(self._sessionString, action, vmId)
        
        if not res[0]:
            raise Exception(res[1])
        
    def getVmInfo(self, vmId):
        ret, info = self.rpc.one.vm.info(self._sessionString, vmId)
        
        if not ret:
            raise Exception(info)
        else:
            return info
        
    def getVmState(self, vmId):
        info = '/tmp/stratus-test.nfo'
        filePutContents(info, self.getVmInfo(vmId))
        tree = ElementTree()
        tree.parse(info)
        status = tree.find('STATE')
        return int(status.text)
        