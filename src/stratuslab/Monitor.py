import sys
import os

from stratuslab.installator.one import OneInstallator
from stratuslab.Util import assignAttributes
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from HostInfo import HostInfo

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

class Monitor(OneInstallator):

    def __init__(self, options, config):
        self.config = config
        self.deRegister = False
        assignAttributes(self, options)
        
        self._setCloud()        

        self.hostInfoDetailAttributes = (('id',4), ('name',16), ('im_mad',8), ('vm_mad',8), ('tm_mad',8))
        self.hostInfoListAttributes = (('id',4), ('name',16))
        
        self.vmInfoDetailAttributes = (('id',4), ('name',16), ('state',4))
        self.vmInfoListAttributes = (('id',4), ('name',16))
        
    def _setCloud(self):
        self.cloud = CloudConnectorFactory.getCloud()

        endpointEnv = 'STRATUSLAB_ENDPOINT'

        if endpointEnv in os.environ:
            self.cloud.setEndpoint(os.environ[endpointEnv])
        else:
            self.cloud.setFrontend(self.config.get('frontend_ip'),
                                   self.config.get('one_port'))

        self.cloud.setCredentials(self.config.get('one_username'),
                                  self.config.get('one_password'))

    def monitor(self, nodeIds):
        infoList = []
        for id in nodeIds:
            infoList.append(self._monitor(id))
        return infoList

    def _monitor(self, id):
        res = self.cloud.getHostInfo(int(id))
        host = etree.fromstring(res)
        info = HostInfo()
        info.populateHosts(host)
        return info

    def vmDetail(self, ids):
        infoList = []
        for id in ids:
            infoList.append(self._vmDetail(id))
        return infoList

    def _vmDetail(self, id):
        res = self.cloud.getVmInfo(int(id))
        host = etree.fromstring(res)
        info = HostInfo()
        info.populateHosts(host)
        print info
        return info

    def _printList(self, infoList):
        for info in infoList:
            self._printInfo(info, self.hostInfoListAttributes)

    def list(self):
        res = self.cloud.listHosts()
        xml = etree.fromstring(res)
        hosts = xml.findall('HOST')
        infoList = []
        for host in hosts:
            info = HostInfo()
            info.populateHosts(host)
            infoList.append(info)
        return infoList

    def listVms(self):
        res = self.cloud.listVms()
        xml = etree.fromstring(res)
        print xml
        hosts = xml.findall('VM')
        infoList = []
        for host in hosts:
            info = HostInfo()
            info.populateHosts(host)
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
