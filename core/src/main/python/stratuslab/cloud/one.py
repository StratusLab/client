#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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

        self.statusLabel = ['init',
                            'pending',
                            'hold',
                            'active',
                            'stopped',
                            'suspended',
                            'done',
                            'failed']
        self.status = {};
        for i in range(len(self.statusLabel)):
            self.status[self.statusLabel[i]] = i

        self.lcmStatusLabel = ['lcm_init',
                               'prolog',
                               'boot',
                               'running',
                               'migrate',
                               'save_stop',
                               'save_suspend',
                               'save_migrate',
                               'prolog_migrate',
                               'prolog_resume',
                               'epilog_stop',
                               'epilog',
                               'shutdown',
                               'cancel',
                               'failure',
                               'delete',
                               'unknown']
        self.lcmStatus = {};
        for i in range(len(self.lcmStatusLabel)):
            self.lcmStatus[self.lcmStatusLabel[i]] = i

        self._sessionString = None
        self._rpc = None
    
    def setEndpointFromParts(self, server, port):
        self.server = 'http://%s:%s/RPC2' % (server, port)
        self.setEndpoint(self.server)

    def setEndpoint(self, address):
        self.server = address
        self._createRpcConnection()

    def _createRpcConnection(self):
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
        if self.getVmLcmStateLabel(vmId) != 'running' :
            return False
        
        return self.vmAction(vmId, 'shutdown')
        
    def vmKill(self, vmId):
        return self.vmAction(vmId, 'finalize')
        
    def addStateLabels(self, xml):
        stateElement = xml.find('STATE')
        state = int(stateElement.text)
        labelElement = etree.Element('STATE_LABEL')
        labelElement.text = self.statusLabel[state]
        xml.append(labelElement);
        
        stateElement = xml.find('LCM_STATE')
        state = int(stateElement.text)
        labelElement = etree.Element('LCM_STATE_LABEL')
        labelElement.text = self.lcmStatusLabel[state]
        xml.append(labelElement)
        
    def listVms(self):
        ret, info = self._rpc.one.vmpool.info(self._sessionString, 0)
        
        if not ret:
            raise Exception(info)

        vmlist = etree.fromstring(info)
        for xml in vmlist.findall('VM'):
            self.addStateLabels(xml)

        return etree.tostring(vmlist)
        
    def getVmInfo(self, vmId):
        ret, info = self._rpc.one.vm.info(self._sessionString, vmId)
        
        if not ret:
            raise Exception(info)

        xml = etree.fromstring(info)

        self.addStateLabels(xml)

        return etree.tostring(xml)

    def getVmState(self, vmId):
        xml = etree.fromstring(self.getVmInfo(vmId))
        status = xml.find('STATE')
        return int(status.text)
    
    def getVmStateLabel(self, vmId):
        status = self.getVmState(self, vmId)
        return self.statusLabel[status]
    
    def getVmLcmState(self, vmId):
        xml = etree.fromstring(self.getVmInfo(vmId))
        status = xml.find('LCM_STATE')
        return int(status.text)
    
    def getVmLcmStateLabel(self, vmId):
        status = self.getVmLcmState(self, vmId)
        return self.lcmStatusLabel[status]
    
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
            vmBooting = self.getVmLcmState(vmId) < self.lcmStatus.get('running')
            if not vmBooting:
                initPhase -= 1
            vmRunning = initPhase == 0 and not vmBooting
            if ticks:
                sys.stdout.flush()
                sys.stdout.write('.')
            time.sleep(1)
            
            if time.time() - start > timeout:
                return False

        return self.getVmLcmState(vmId) == self.lcmStatus.get('running')
    
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
