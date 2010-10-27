import sys
import os

from stratuslab.installator.one import OneInstallator
from stratuslab.Util import assignAttributes
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.CloudInfo import CloudInfo
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Configurable import Configurable

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
        
        self.vmInfoDetailAttributes = (('id',4), ('state',8), ('cpu', 8), ('memory', 8), ('ip', 16))
        self.vmInfoListAttributes = (('id',4), ('name',16))
        
    def _setCloud(self):
        self.cloud = CloudConnectorFactory.getCloud()

        endpointEnv = 'STRATUSLAB_ENDPOINT'

        if endpointEnv in os.environ:
            self.cloud.setEndpoint(os.environ[endpointEnv])
        elif 'frontendIp' in self.__dict__ and 'onePort' in self.__dict__:
            self.cloud.setEndpointFromParts(self.frontendIp, self.onePort)
        else:
            self.cloud.setEndpoint(self.endpoint)

        self.cloud.setCredentials(self.oneUsername, self.onePassword)

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

    def vmKill(self, id):
        return self.cloud.vmKill(int(id))

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
            self._printInfo(item, self.vmInfoDetailAttributes)

    def printVmDetails(self, list):
        self._printInfoHeader(self.vmInfoDetailAttributes)
        for item in list:
            self._printInfo(item, self.vmInfoDetailAttributes)

    def _printInfoHeader(self, headerAttributes):
        for attrib in headerAttributes:
            sys.stdout.write(attrib[0].ljust(int(attrib[1])))
        sys.stdout.write('\n')
    
    def _printInfo(self, info, headerAttributes):
        for attrib in headerAttributes:
            sys.stdout.write(info.__getattribute__(attrib[0]).ljust(int(attrib[1])))
        sys.stdout.write('\n')
