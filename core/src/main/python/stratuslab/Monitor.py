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
import os

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.CloudInfo import CloudInfo
from stratuslab.Configurable import Configurable
from stratuslab.Authn import AuthnFactory
import Util

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

class Monitor(Configurable):
    
    def __init__(self, configHolder):
        super(Monitor, self).__init__(configHolder)

        self._setCloud()

        self.hostInfoDetailAttributes = (('id',4), ('name',16), ('im_mad',8), ('vm_mad',8), ('tm_mad',8))
        self.hostInfoListAttributes = (('id',4), ('name',16))
        
        self.vmInfoDetailAttributes = (('id',4), ('state_summary', 16), ('cpu', 10), ('memory', 10), ('ip', 16))
        self.vmInfoListAttributes = (('id',4), ('state_summary', 16), ('cpu', 10), ('memory', 10), ('ip', 16))
        
        self.labelDecorator = {'state_summary': 'state'}
        
    def _setCloud(self):
        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)

        endpointEnv = 'STRATUSLAB_ENDPOINT'

        if endpointEnv in os.environ:
            self.cloud.setEndpoint(os.environ[endpointEnv])
        elif 'frontendIp' in self.__dict__ and 'proxyPort' in self.__dict__:
            self.cloud.setEndpointFromParts(self.frontendIp, self.proxyPort)
        else:
            self.cloud.setEndpoint(self.endpoint)

    def nodeDetail(self, nodeIds):
        infoList = []
        for id in nodeIds:
            infoList.append(self._nodeDetail(id))
        return infoList

    def _nodeDetail(self, id):
        res = self.cloud.getHostInfo(int(id))
        host = etree.fromstring(res)
        info = CloudInfo()
        info.populate(host)
        return info

    def vmDetail(self, ids):
        infoList = []
        for id in ids:
            infoList.append(self._vmDetail(id))
        return infoList

    def _vmDetail(self, id):
        res = self.cloud.getVmInfo(int(id))
        vm = etree.fromstring(res)
        info = CloudInfo()
        info.populate(vm)
        return info

    def _printList(self, infoList):
        for info in infoList:
            self._printInfo(info, self.hostInfoListAttributes)

    def listNodes(self):
        nodes = self.cloud.listHosts()
        return self._iterate(etree.fromstring(nodes))
        
    def listVms(self):
        vms = self.cloud.listVms()
        return self._iterate(etree.fromstring(vms))

    def _iterate(self, list):
        infoList = []
        for item in list:
            info = CloudInfo()
            info.populate(item)
            infoList.append(info)
        return infoList

    def printList(self, list):
        self._printInfoHeader(self.hostInfoListAttributes)
        for item in list:
            self._printInfo(item, self.hostInfoDetailAttributes)

    def printDetails(self, list):
        self._printInfoHeader(self.hostInfoDetailAttributes)
        for item in list:
            self._printInfo(item, self.hostInfoDetailAttributes)

    def printVmList(self, list):
        self._printInfoHeader(self.vmInfoListAttributes)
        for item in list:
            self._printInfo(item, self.vmInfoListAttributes)

    def printVmDetails(self, list):
        self._printInfoHeader(self.vmInfoDetailAttributes)
        for item in list:
            self._printInfo(item, self.vmInfoDetailAttributes)


    def _printInfoHeader(self, headerAttributes):
        Util.printEmphasisStart()
        try:
            for attrib in headerAttributes:
                label = self._decorateLabel(attrib[0])
                sys.stdout.write(label.ljust(int(attrib[1])))
        finally:
            Util.printEmphasisStop()
        sys.stdout.write('\n')
        
    def _decorateLabel(self, label):
        return self.labelDecorator.get(label,label)
    
    def _printInfo(self, info, headerAttributes):
        for attrib in headerAttributes:
            sys.stdout.write(getattr(info, attrib[0]).ljust(int(attrib[1])))
        sys.stdout.write('\n')
