#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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

from stratuslab.Exceptions import OneException
from stratuslab import Util

etree = Util.importETree()

class OneConnector(object):

    ACL_USERS = {
        "UID"           : 0x100000000,
        "GID"           : 0x200000000,
        "ALL"           : 0x400000000
    }
    ACL_RESOURCES = {
        "VM"            : 0x1000000000,
        "HOST"          : 0x2000000000,
        "NET"           : 0x4000000000,
        "IMAGE"         : 0x8000000000,
        "USER"          : 0x10000000000,
        "TEMPLATE"      : 0x20000000000,
        "GROUP"         : 0x40000000000
    }
    ACL_RIGHTS = {
        "USE"           : 0x1,  # Auth. to use an object
        "MANAGE"        : 0x2,  # Auth. to perform management actions
        "ADMIN"         : 0x4,  # Auth. to perform administrative actions
        "CREATE"        : 0x8   # Auth. to create an object
    }

    def __init__(self, credentials):

        self._sessionString = None
        self._rpc = None
        self._credentials = credentials

    def setEndpointFromParts(self, server, port=2634, path='xmlrpc', protocol='https'):
        self._setEndpointFromParts(server, port, path, protocol)
        self.setEndpoint(self.server)

    def _setEndpointFromParts(self, server, port=2634, path='xmlrpc', protocol='https'):
        self.server = '%s://%s:%s/%s' % (protocol, server, port, path)

    def setEndpoint(self, address):
        if not address:
            raise ValueError('Missing endpoint')
        if not address.startswith('http'):
            self._setEndpointFromParts(address)
        else:
            self.server = address
        self._createRpcConnection()
        return self.server

    def _createRpcConnection(self):
        self._rpc = self._credentials.createRpcConnection()
        self._sessionString = self._credentials.createSessionString()

    def vmStart(self, vmTpl):
        isSuccess, detail, error_code = self._rpc.one.vm.allocate(self._sessionString, vmTpl)

        self._raiseIfError(isSuccess, detail)

        vmId = detail

        return vmId

    def vmStop(self, vmId):
        self._vmAction(vmId, 'shutdown')

    def vmKill(self, vmId):
        self._vmAction(vmId, 'finalize')

    def _vmAction(self, vmId, action):

        res = self._rpc.one.vm.action(self._sessionString, action, vmId)

        isSuccess = res[0]
        detail = ''
        if len(res) > 1:
            detail = res[1]

        self._raiseIfError(isSuccess, detail)

        return

    def _raiseIfError(self, isSuccess, reason):
        if not isSuccess:
            raise OneException(reason)

    def listVms(self, showVmsFromAllUsers=False):
        fromAllUsers = -2
        currentUserOnly = -3

        if showVmsFromAllUsers:
            visibilitySwitch = fromAllUsers
        else:
            visibilitySwitch = currentUserOnly

        ret, info, error_code = self._rpc.one.vmpool.info(self._sessionString, visibilitySwitch, -1, -1, -1)

        if not ret:
            raise OneException(info)

        vmlist = etree.fromstring(info)
        for xml in vmlist.findall('VM'):
            self._addStateSummary(xml)

        return etree.tostring(vmlist)

    def _getVmInfoAsXml(self, vmId):
        info = self._vmInfo(vmId)

        xml = etree.fromstring(info)

        self._addStateSummary(xml)

        return xml

    def _addStateSummary(self, xml):
        vmState = self._getOneVmStateFromXml(xml)

        labelElement = etree.Element('STATE_SUMMARY')
        labelElement.text = str(vmState)
        xml.append(labelElement)

    def _vmInfo(self, vmId):
        isSuccess, info, error_code = self._rpc.one.vm.info(self._sessionString, vmId)
        self._raiseIfError(isSuccess, info)
        return info

    def getVmInfo(self, vmId):
        info = self._vmInfo(vmId)
        xml = etree.fromstring(info)
        self._addStateSummary(xml)
        return etree.tostring(xml)
    
    def getVmNode(self, vmId):
        info = self._vmInfo(vmId)
        xml = etree.fromstring(info)
        return xml.find('HISTORY_RECORDS/HISTORY/HOSTNAME').text
    
    def getVmOwner(self, vmId):
        info = self._vmInfo(vmId)
        xml = etree.fromstring(info)
        return xml.find('UNAME').text
    
    def getVmDiskSource(self, vmId, diskId):
        info = self._vmInfo(vmId)
        xml = etree.fromstring(info)
        sources = [x.find('SOURCE').text for x in xml.findall('TEMPLATE/DISK') 
                   if x.find('DISK_ID').text == str(diskId)]
        return sources[0]
    
    def getCreateImageInfo(self, vmId):
        info = self._vmInfo(vmId)
        xml = etree.fromstring(info)
        createImageElem = 'TEMPLATE/CREATE_IMAGE'
        infos = {
             'creatorEmail': xml.find('%s/CREATOR_EMAIL' % createImageElem).text,
             'creatorName': xml.find('%s/CREATOR_NAME' % createImageElem).text,
             'newImageComment': xml.find('%s/NEWIMAGE_COMMENT' % createImageElem).text,
             'newImageVersion': xml.find('%s/NEWIMAGE_VERSION' % createImageElem).text,
             'newImageMarketplace': self._findXmlText(xml, '%s/NEWIMAGE_MARKETPLACE' % createImageElem)
        }
        return infos
    
    def _findXmlText(self, xml, query):
        return xml.find(query).text.strip('"')
    
    def isVmRunning(self, vmId):
        return str(self._getVmStateSummary(vmId)) == 'Running'
    
    def _getOneVmStateFromXml(self, xml):
        stateElement = self._getStateElement(xml)
        state = int(stateElement.text)

        stateElement = self._getLcmStateElement(xml)
        lcmState = int(stateElement.text)

        return OneVmState(state, lcmState)

    def _getVmLcmStateLabel(self, vmId):
        status = self._getVmLcmState(vmId)
        return self.lcmStatusLabel[status]

    def _getVmLcmState(self, vmId):
        xml = self._getVmStateAsXml(vmId)
        status = self._getLcmStateElement(xml)
        return int(status.text)

    def _getStateElement(self, xml):
        return xml.find('STATE')

    def _getLcmStateElement(self, xml):
        return xml.find('LCM_STATE')

    def getVmIp(self, vmId):
        xml = self._getVmInfoAsXml(vmId)

        nic = xml.find('TEMPLATE/NIC')
        networkName = nic.find('NETWORK').text
        ip = nic.find('IP').text

        return networkName, ip

    def getVmSshPort(self, *args, **kwargs):
        return 22

    def getVmState(self, vmId):
        return str(self._getVmStateSummary(vmId))

    def waitUntilVmRunningOrTimeout(self, vmId, timeout, ticks=True, failOn=()):
        start = time.time()
        state = ''

        noWaitStates = ('Running','Failed')

        while (str(state) not in noWaitStates):

            state = self._getVmStateSummary(vmId)

            if str(state) in failOn:
                return False

            if ticks:
                sys.stdout.flush()
                sys.stdout.write('.')
            time.sleep(1)

            if time.time() - start > timeout:
                if ticks:
                    sys.stdout.flush()
                    sys.stdout.write('\n')
                return False

        if ticks:
            sys.stdout.flush()
            sys.stdout.write('\n')
        return True

    def _getVmStateSummary(self, vmId):
        info = self._vmInfo(vmId)
        xml = etree.fromstring(info)
        return self._getOneVmStateFromXml(xml)

    # -------------------------------------------
    #    Virtual network management
    # -------------------------------------------

    def networkCreate(self, vnetTpl):
        ret, id, error_code = self._rpc.one.vn.allocate(self._sessionString, vnetTpl)

        if not ret:
            error = id
            raise OneException('Error creating ONE network:\n%s' % error)

        return id

    def getNetworkPoolInfo(self, filter=-2):
        ret, info, error_code = self._rpc.one.vnpool.info(self._sessionString, filter)

        if not ret:
            raise OneException(info)

        return info

    def getNetworkInfo(self, vnetId):
        ret, info, error_code = self._rpc.one.vn.info(self._sessionString, vnetId)

        if not ret:
            raise OneException(info)

        return info

    # -------------------------------------------
    #    Host management
    # -------------------------------------------

    def hostCreate(self, hostname, im, vmm, tm, vnm='dummy', inDomain=True):
        ret, id, error_code = self._rpc.one.host.allocate(self._sessionString, hostname, im, vmm, vnm, tm, inDomain)

        if not ret:
            raise OneException(id)

        return id

    def hostRemove(self, id):
        ret = self._rpc.one.host.delete(self._sessionString, id)

        if not ret:
            raise OneException(id)

        return id

    def getHostInfo(self, id):
        ret, info, error_code = self._rpc.one.host.info(self._sessionString, id)

        if not ret:
            raise OneException(info)

        return info

    def listHosts(self):
        ret, info, error_code = self._rpc.one.hostpool.info(self._sessionString)

        if not ret:
            raise OneException(info)

        return info

    # -------------------------------------------
    #    ACLs management
    # -------------------------------------------

    def addNetworkAcl(self, users, net_id_int, rights):
        """
        users - hex
        net_id_int - integer, network ID
        rights - hex
        """
        # "magic" number
        _magic = self.ACL_USERS['UID']
        net_resource = hex(self.ACL_RESOURCES['NET'] + _magic + net_id_int)
 
        ret, info, error_code = self._rpc.one.acl.addrule(self._sessionString,
                                                          users,
                                                          net_resource,
                                                          rights)

        if not ret:
            raise OneException(info)

        return info

    def addUserAcl(self, users, resources, rights):
        ret, info, error_code = self._rpc.one.acl.addrule(self._sessionString,
                                                          users,
                                                          resources,
                                                          rights)
        if not ret:
            raise OneException(info)

        return info

class OneVmState(object):

    def __init__(self, state, lcmState = None):
        self. state = int(state)

        self.lcmState = lcmState

        self.invalidState = 'Invalid state'

        self.stateDefinition = ['init',
                                'pending',
                                'hold',
                                'active',
                                'stopped',
                                'suspended',
                                'done',
                                'failed']

        self.lcmStateDefintion = ['lcm_init',
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

    def __str__(self):
        if self._useLcmState():
            str = self._lcmStateToString()
        else:
            str = self._stateToString()
        return str.title()

    def _useLcmState(self):
        stateForLcmStateLookup = 3
        return self.state == stateForLcmStateLookup

    def _stateToString(self):
        if (self.state < 0) and (self.state >= len(self.stateDefinition)):
            return self.invalidState
        return self.stateDefinition[self.state]

    def _lcmStateToString(self):
        lcm = self._lcmStateAsInt()
        if (lcm != None) and (lcm >= 0) and (lcm < len(self.lcmStateDefintion)):
            return self.lcmStateDefintion[lcm]
        else:
            Util.printError('Invalid state: %s' % lcm, exit=False)
            return self.invalidState

    def _lcmStateAsInt(self):
        lcm = None
        if self.lcmState:
            lcm = int(self.lcmState)
        return lcm


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
