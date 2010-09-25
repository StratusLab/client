import sys
import time
import xmlrpclib

from stratuslab.Util import networkSizeToNetmask
from stratuslab.Util import shaHexDigest
from stratuslab.Util import unifyNetsize

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
        self.status = {'prolog': 1,
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
            'unknown': 16}
        
        self._sessionString = None
        self._rpc = None
    
    def setFrontend(self, server, port):
        self.server = 'http://%s:%s/RPC2' % (server, port)
        self._createRpcConnection()

    def setEndpoint(self, address):
        self.server = address
        self._createRpcConnection()

    def setCredentials(self, username, password):
        self._sessionString = '%s:%s' % (username, shaHexDigest(password))

    def _createRpcConnection(self):
        self._rpc = xmlrpclib.ServerProxy(self.server)

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
        
    def listVms(self):
        ret, info = self._rpc.one.vmpool.info(self._sessionString, 0)
        
        if not ret:
            raise Exception(info)
        
        return info
        
    def getVmInfo(self, vmId):
        ret, info = self._rpc.one.vm.info(self._sessionString, vmId)
        
        if not ret:
            raise Exception(info)
        
        return info
        
    def getVmState(self, vmId):
        xml = etree.fromstring(self.getVmInfo(vmId))
        status = xml.find('STATE')
        return int(status.text)
    
    def getVmIp(self, vmId):
        xml = etree.fromstring(self.getVmInfo(vmId))
        
        vmAddress = {}
        for nic in xml.findall('TEMPLATE/NIC'):
            vmAddress[nic.find('NETWORK').text] = nic.find('IP').text
        
        return vmAddress

    def getVmSshPort(self, *args, **kwargs):
        return 22
            
    def waitUntilVmRunningOrTimeout(self, vmId, timeout, ticks=True):
        start = time.time()
        # FIXME: Hack to wait for VM completely started
        vmBooting = True
        vmRunning = False
        initPhase = 15
        while not vmRunning:
            vmBooting = self.getVmState(vmId) < self.status.get('running')
            if not vmBooting:
                initPhase -= 1
            vmRunning = initPhase == 0 and not vmBooting
            if ticks:
                sys.stdout.flush()
                sys.stdout.write('.')
            time.sleep(1)
            
            if time.time() - start > timeout:
                return False

        return self.getVmState(vmId) == self.status.get('running')
    
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

        return info

    def networkNameToId(self, vnetName):
        xml = etree.fromstring(self.getNetworkPoolInfo())
        names = xml.findall('VNET/NAME')
        ids = xml.findall('VNET/ID')
        vnets = zip(names, ids)

        for name, id in vnets:
            if name.text == vnetName:
                return int(id.text)

    def getNetworkAddress(self, vnetId):
        xml = etree.fromstring(self.getNetworkInfo(vnetId))

        addresses = []
        try:
            addresses = xml.find('TEMPLATE/NETWORK_ADDRESS').text
        except:
            pass

        return addresses

    def getNetworkNetmask(self, vnetId):
        xml = etree.fromstring(self.getNetworkInfo(vnetId))

        netmask = ''
        
        try:
            addr = xml.find('TEMPLATE/NETWORK_SIZE').text
            netmask = networkSizeToNetmask(unifyNetsize(addr))
        except:
            pass

        return netmask

    def addPublicInterface(self, vmTpl):
        # We assume the is a public network
        vmTpl += '\nNIC = [ NETWORK = "public" ]\n'
        return vmTpl
        
    # -------------------------------------------
    #    Host management
    # -------------------------------------------

    def hostCreate(self, hostname, im, vmm, tm, inDomain=True):
        ret, id = self._rpc.one.host.allocate(self._sessionString, hostname, im, vmm, tm, inDomain)

        if not ret:
            raise Exception(id)

        return id

    def hostRemove(self, id):
        ret = self._rpc.one.host.delete(self._sessionString, id)

        if not ret:
            raise Exception(id)

        return id

    def getHostInfo(self, id):
        ret, info = self._rpc.one.host.info(self._sessionString, id)

        if not ret:
            raise Exception(info)

        return info

    def listHosts(self):
        ret, info = self._rpc.one.hostpool.info(self._sessionString)

        if not ret:
            raise Exception(info)

        return info

class OneVmState(object):
    
    def __init__(self, state, lcmState = None):
        self. state = state
        self.lcmState = lcmState

        self.invalidState = 'Invalid state'

        self.stateDefinition = {'0': 'Init',
                                '1': 'Pending',
                                '2': 'Hold',
                                '3': 'Active',
                                '4': 'Stopped',
                                '5': 'Suspended',
                                '6': 'Done',
                                '7': 'Failed'}
        
        self.lcmStateDefintion = {'0': 'LCM_INIT',
                                  '1': 'PROLOG',
                                  '2': 'BOOT',
                                  '3': 'RUNNING',
                                  '4': 'MIGRATE',
                                  '5': 'SAVE_STOP',
                                  '6': 'SAVE_SUSPEND',
                                  '7': 'SAVE_MIGRATE',
                                  '8': 'PROLOG_MIGRATE',
                                  '9': 'PROLOG_RESUME',
                                  '10': 'EPILOG_STOP',
                                  '11': 'EPILOG',
                                  '12': 'SHUTDOWN',
                                  '13': 'CANCEL',
                                  '14': 'FAILURE',
                                  '15': 'DELETE',
                                  '16': 'UNKNOWN'}

    def __str__(self):
        if self._useLcmState():
            str = self._lcmStateToString()
        else:
            str = self._stateToString()
        return str.title()
    
    def _useLcmState(self):
        stateForLcmStateLookup = 3
        return str(self.state) == str(stateForLcmStateLookup)
    
    def _stateToString(self):
        if self.state not in self.stateDefinition:
            return self.invalidState
        return self.stateDefinition.get(self.state, self.invalidState)

    def _lcmStateToString(self):
        if self.lcmState not in self.lcmStateDefintion:
            return self.invalidState
        return self.lcmStateDefintion.get(self.lcmState, self.invalidState)
    
    
class OneHostState(object):
    
    def __init__(self, state):
        self. state = state
        self.invalidState = 'Invalid state'
        self.stateDefinition = {'0': 'INIT',
                                '1': 'MONITORING',
                                '2': 'MONITORED',
                                '3': 'ERROR',
                                '4': 'DISABLED'}

    def __str__(self):
        return self.stateDefinition.get(self.state,self.invalidState).title()