import xmlrpclib
import time
import sys
from stratuslab.Util import shaHexDigest

try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise Exception("Failed to import ElementTree from any known place")

# TODO: Create a CloudConnector base class
class OneConnector(object):
    
    def __init__(self):
        # TODO: Verify status with ONE's guys
        self.status = { 'prolog': 1,
                        'boot':  2,
                        'running': 3,
                        'migrate': 4,
                        'save_stop': 5,
                        'save_suspend': 6,
                        'save_migrate': 7,
                        'prolog_migrate': 8,
                        'prolog_resume': 9,
                        'epilog_stop': 10,
                        'epilog': 11,
                        'shutdown': 12,
                        'cancel': 13,
                        'failure': 14,
                        'delete': 15,
                        'unknown': 16 }
        
        self._sessionString = None
        self._rpc = None
    
    def setFrontend(self, server, port):
        self.server = 'http://%s:%s/RPC2' % (server, port)
        self._rpc = xmlrpclib.ServerProxy(self.server)
    
    def setCredentials(self, username, password):
        self._sessionString = '%s:%s' % (username, shaHexDigest(password))
        
    # -------------------------------------------
    #    Virtual machine management
    # -------------------------------------------
        
    def vmStart(self, vmTpl):
        ret, vmId = self._rpc.one.vm.allocate(self._sessionString, vmTpl)
        
        if not ret:
            raise Exception(vmId)

        return vmId
    
    def vmAction(self, vmId, action):
        res = self._rpc.one.vm.action(self._sessionString, action, vmId)
        
        # TODO: Fill ONE bug report
        if not res[0]:
            raise Exception(res[1])
        
        return res
        
    def vmStop(self, vmId):
        if self.getVmState(vmId) != self.status.get('running'):
            return False
        
        return self.vmAction(vmId, 'shutdown')
        
    def getVmInfo(self, vmId, xml=False):
        ret, info = self._rpc.one.vm.info(self._sessionString, vmId)
        
        if not ret:
            raise Exception(info)
        
        # TODO: Return a dictionary
        if not xml:
            pass
        
        return info
        
    def getVmState(self, vmId):
        xml = etree.fromstring(self.getVmInfo(vmId, True))
        status = xml.find('STATE')
        return int(status.text)
    
    def getVmIp(self, vmId):
        xml = etree.fromstring(self.getVmInfo(vmId, True))
        
        vmAddress = {}
        for nic in xml.findall('TEMPLATE/NIC'):
            vmAddress[nic.find('NETWORK').text] = nic.find('IP').text
        
        return vmAddress
    
            
    def waitUntilVmRunningOrTimeout(self, vmId, timeout, ticks=True):
        start = time.time()
        while self.getVmState(vmId) < self.status.get('running'):
            if ticks:
                sys.stdout.flush()
                sys.stdout.write('.')
            time.sleep(1)
            
            if time.time() - start > timeout:
                return False
            
        # Wait VM to be completely started
        time.sleep(3)

        return self.getVmState(vmId) == 3
    
    # -------------------------------------------
    #    Virtual network management
    # -------------------------------------------
        
    def networkCreate(self, vnetTpl):
        ret, id = self._rpc.one.vn.allocate(self._sessionString, vnetTpl)
        
        if not ret:
            raise Exception(id)
        
        return id
    
    def getNetworkPoolInfo(self, filter=-2):
        ret, info = self._rpc.one.vnpool.info(self._sessionString, filter)
        
        if not ret:
            raise Exception(info)
        
        return info
        
    def getNetworkPoolNames(self):
        xml = etree.fromstring(self.getNetworkPoolInfo())
        vnets = xml.findall('VNET/NAME')
        
        return [i.text for i in vnets]
        
    def getNetworkInfo(self, vnetId):
        ret, info = self._rpc.one.vn.info(self._sessionString, vnetId)
        
        if not ret:
            raise Exception(info)
        else:
            return info
        