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

import socket
import signal

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.CloudInfo import CloudInfo
from stratuslab.Configurable import Configurable
from stratuslab.Authn import AuthnFactory
import stratuslab.Util as Util
from stratuslab.pat.Client import PortTranslationWebClient

etree = Util.importETree()


class Monitor(Configurable):
    TEMPLATE_NIC_IP = 'template_nic_ip'
    TEMPLATE_NIC_HOSTNAME = 'template_nic_hostname'

    ipToHostname = True

    @staticmethod
    def addOptions(parser):
        parser.add_option('-n', dest='ipToHostname', action='store_false',
                          help='Don\'t do reverse DNS resolution - print IPs of instances.',
                          default=Monitor.ipToHostname)

    def __init__(self, configHolder):
        self.endpoint = None
        self.verboseLevel = 1
        self.portTranslation = False
        self.portTranslationClient = None

        super(Monitor, self).__init__(configHolder)

        self._setCloud()

        self.hostInfoDetailAttributes = (['id', 4], ['name', 16], ['im_mad', 8], ['vm_mad', 8], ['tm_mad', 8])
        self.hostInfoListAttributes = (['id', 4], ['name', 16])

        self.vmInfoDetailAttributes = [['id', 4], ['state_summary', 10], ['template_vcpu', 5], ['memory', 10],
                                       ['cpu', 5], [Monitor.TEMPLATE_NIC_HOSTNAME, 24], ['name', 16]]
        self.vmInfoListAttributes = [['id', 4], ['state_summary', 10], ['template_vcpu', 5], ['memory', 10], ['cpu', 5],
                                     [Monitor.TEMPLATE_NIC_HOSTNAME, 24], ['name', 16]]

        self.labelDecorator = {'state_summary': 'state', Monitor.TEMPLATE_NIC_HOSTNAME: 'host/ip',
                               Monitor.TEMPLATE_NIC_IP: 'ip', 'template_vcpu': 'vcpu', 'cpu': 'cpu%'}

        if Util.isTrueConfVal(self.portTranslation):
            self.portTranslationClient = PortTranslationWebClient(configHolder)
            self.vmInfoDetailAttributes.insert(-1, ['template_pat', 16])
            self.vmInfoListAttributes.insert(-1, ['template_pat', 16])
            self.labelDecorator['template_pat'] = 'pat(VM:GW)'

    def _setCloud(self):
        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)

        if self.endpoint:
            self.cloud.setEndpoint(self.endpoint)
        elif 'frontendIp' in self.__dict__ and 'proxyPort' in self.__dict__:
            self.cloud.setEndpointFromParts(self.frontendIp, self.proxyPort)
        else:
            self.cloud.setEndpoint(self.endpoint)

    def nodeDetail(self, nodeIds):
        infoList = []
        for nodeId in nodeIds:
            infoList.append(self._nodeDetail(nodeId))
        return infoList

    def _nodeDetail(self, nodeId):
        res = self.cloud.getHostInfo(int(nodeId))
        host = Util.etree_from_text(res)
        info = CloudInfo()
        info.populate(host)
        return info

    def vmDetail(self, vmIds):
        infoList = []
        for vmId in vmIds:
            infoList.append(self._vmDetail(vmId))
        return infoList

    def _vmDetail(self, vmId):
        res = self.cloud.getVmInfo(int(vmId))
        vm = Util.etree_from_text(res)
        if self.portTranslationClient:
            self.portTranslationClient.addPortTranslationToSingleVmInfo(vm)
        info = CloudInfo()
        info.populate(vm)
        self._addHostnameElement(info)
        return info

    def _addHostnameElement(self, info):
        ip = info.attribs[Monitor.TEMPLATE_NIC_IP]
        info.set(Monitor.TEMPLATE_NIC_HOSTNAME, self._ipv4ToHostname(ip))

    def _addHostnameToVmsInfo(self, vmsInfo):
        for vmInfo in vmsInfo.findall('VM'):
            self._addHostnameToSingleVmInfo(vmInfo)

    def _addHostnameToSingleVmInfo(self, vmInfo):
        for nic in vmInfo.findall('TEMPLATE/NIC'):
            ipv4 = nic.find('IP').text
            hostname = self._ipv4ToHostname(ipv4)

            host_element = etree.Element("HOSTNAME")
            host_element.text = hostname

            nic.append(host_element)

    def _ipv4ToHostname(self, ipv4):
        if self.ipToHostname:
            try:
                return socket.gethostbyaddr(ipv4)[0]
            except:
                pass
        return ipv4

    def listNodes(self):
        nodes = self.cloud.listHosts()
        correct_nodes = []
        for node in self._iterate(Util.etree_from_text(nodes)):
            # FIXME: remove this later.
            try:
                node.attribs['template_usedcpu'] = round(float(node.attribs['template_usedcpu']), 2)
            except:
                pass
            correct_nodes.append(node)
        return correct_nodes

    def listVms(self, showVmsFromAllUsers=False):
        res = self.cloud.listVms(showVmsFromAllUsers)
        vms = Util.etree_from_text(res)

        self._addHostnameToVmsInfo(vms)

        if self.portTranslationClient:
            self.portTranslationClient.addPortTranslationToVmsInfo(vms)

        correct_vms = []
        for vm in self._iterate(vms):
            self._addHostnameElement(vm)
            if vm.attribs['uname'].startswith('CN'):
                vm.attribs['uname'] = vm.attribs['uname'].replace("CN%3D", "") \
                    .replace("%2COU%3D", " OrgUnit:").replace("%2CO%3D", " Org:").replace("%2CC%3D", " Country:") \
                    .replace("+", " ")
            correct_vms.append(vm)
        return correct_vms

    def _iterate(self, items):
        infoList = []
        for item in items:
            info = CloudInfo()
            info.populate(item)
            infoList.append(info)
        return infoList

    def formatVmList(self, items):
        self._adjustVmAttributeFields(items)
        result = self._formatVmInfoHeader(self.vmInfoListAttributes)
        for item in items:
            result += self._formatVmInfo(item, self.vmInfoListAttributes)
        return result

    def formatVmDetails(self, items):
        self._adjustVmAttributeFields(items)
        result = self._formatVmInfoHeader(self.vmInfoDetailAttributes)
        for item in items:
            result += self._formatVmInfo(item, self.vmInfoDetailAttributes)
        return result

    def formatVmAllAttributes(self, vmInfoList):
        result = ''
        for vmInfo in vmInfoList:
            vmAttributes = vmInfo.getAttributes()
            result = '%s\n' % ('-' * 25)
            result += '%s (all attributes)\n' % vmAttributes['id']
            for k in sorted(vmAttributes.keys()):
                result += '  %s = %s\n' % (k, vmAttributes[k])
        return result

    def _formatVmInfoHeader(self, headerAttributes):
        result = ''

        try:
            for attrib in headerAttributes[:-1]:
                label = self._decorateLabel(attrib[0])
                result += label.ljust(int(attrib[1]))
                # adjust last element to its own length

            attrib = headerAttributes[-1]
            label = self._decorateLabel(attrib[0])
            result += label.ljust(len(attrib[0]))
        finally:
            result += "\n"

        return result

    def _decorateLabel(self, label):
        return self.labelDecorator.get(label, label)

    def _formatVmInfo(self, info, headerAttributes):
        result = ''
        for attrib in headerAttributes[:-1]:
            result += getattr(info, attrib[0], '').ljust(int(attrib[1]))
        result += self._formatVmName(headerAttributes, info)

        result += self._formatErrorIfRequired(info, headerAttributes)

        return result

    def _formatVmName(self, headerAttributes, info):
        # adjust last element to its own length
        attrib = headerAttributes[-1]
        return getattr(info, attrib[0]).ljust(len(attrib[0])) + "\n"

    def _formatErrorIfRequired(self, info, headerAttributes):
        result = ''
        if self.verboseLevel >= Util.VERBOSE_LEVEL_NORMAL:
            if getattr(info, 'template_error_message', None):
                result = ' ' * headerAttributes[0][1] + info.template_error_message.strip() + '\n'

        return result

    def _adjustVmAttributeFields(self, _list):
        attrList = ('vmInfoDetailAttributes', 'vmInfoListAttributes')
        self._adjustAttributeFields(_list, attrList)

    def _adjustHostAttributeFields(self, _list):
        attrList = ('hostInfoDetailAttributes', 'hostInfoDetailAttributes')
        self._adjustAttributeFields(_list, attrList)

    def _adjustAttributeFields(self, _list, attrList):
        if _list:
            for attr in attrList:
                for i, attrVal in enumerate(getattr(self, attr)):
                    lenMax = max(map(lambda x: len(getattr(x, attrVal[0], '') or ''), _list))
                    if lenMax >= getattr(self, attr)[i][1]:
                        getattr(self, attr)[i][1] = lenMax + 1

    def getVmConnectionInfo(self, vmId):
        host, port = None, None

        vmPort = str(self.cloud.getVmSshPort(int(vmId)))
        vmInfo = self._vmDetail(vmId)
        if self.portTranslationClient and self.portTranslationClient.hasPortTranslated(vmInfo):
            port = self.portTranslationClient.findGatewayPort(vmInfo, vmPort)
            host = self.patGatewayHost
        else:
            port = vmPort
            host = getattr(vmInfo, Monitor.TEMPLATE_NIC_IP, None)
        return host, port


class MultisiteMonitor(object):
    def __init__(self, configHolder):
        self.endpointTimeout = '5'
        self.configHolder = configHolder
        configHolder.assign(self)
        self.endpoints = [eup.strip().split() for eup in self.endpoints.split('\n')]

    def formatVmList(self):
        configHolder = self.configHolder.copy()

        result = ''
        for endpoint, username, password in self.endpoints:
            result += '::: %s : %s :::' % (endpoint, username)

            configHolder.set('endpoint', endpoint)
            configHolder.set('username', username)
            configHolder.set('password', password)
            monitor = Monitor(configHolder)
            self._set_alarm()
            try:
                vmList = monitor.listVms()
                result += monitor.formatVmList(vmList)
            except Exception, ex:
                Util.printError(str(ex))
            except KeyboardInterrupt:
                pass
            self._unset_alarm()

        return result

    def _set_alarm(self):
        def _sig_handler(_ignore1, _ignore2):
            raise Exception("WARNING: Could not get results in %s s" %
                            self.endpointTimeout)

        signal.signal(signal.SIGALRM, _sig_handler)
        signal.alarm(int(self.endpointTimeout))

    def _unset_alarm(self):
        signal.alarm(0)
