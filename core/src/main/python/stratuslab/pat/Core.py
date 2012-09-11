#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552.
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique
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

from stratuslab import Util

etree = Util.importETree()

class PortTranslation(object):

    def __init__(self, configHolder):
        self.verboseLevel = 0
        configHolder.assign(self)

    def isTranslatedNetwork(self, network):
        return Util.isTrueConfVal(self.portTranslation) and network in self.patNetworks

    def hasPortTranslated(self, vmInfo):
        if getattr(vmInfo, 'template_pat', None):
            return True
        return False

    def findGatewayPort(self, vmInfo, port):
        ports = getattr(vmInfo, 'template_pat', None)
        vmPorts = VmPortTranslation(ports)
        return vmPorts.findGwPortFromVmPort(port)

    def addPortTranslationToVmsInfo(self, vmsInfo):
        # Get all ports in one request to avoid too many access to
        # PortTranslation service.
        vmsPorts = self.getPortTranslation()
        for vmInfo in vmsInfo.findall('VM'):
            vmId = vmInfo.find('ID').text
            vmPorts = vmsPorts.get(vmId, VmPortTranslation(vmid=vmId))
            self.addPortTranslationToSingleVmInfo(vmInfo, vmPorts)

    def addPortTranslationToSingleVmInfo(self, vmInfo, vmPorts=None):
        vmId = vmInfo.find('ID').text
        vmTemplate = vmInfo.find('TEMPLATE')

        if vmPorts is None:
            vmPorts = self.getVmPortTranslation(vmId)

        if len(vmPorts):
            labelElement = etree.Element('PAT')
            labelElement.text = vmPorts.toString()
            vmTemplate.append(labelElement)
        # FIXME: should be a loop over each port translation but doesn't work
        #        because of a bug (JIRA#1036)
        #labelElement = etree.Element('PAT')
        #for vmPort in vmPorts:
        #    labelElement.text = self._formatPortTranslation(vmPort)
        #    vmTemplate.append(labelElement)

    def getAllPortTranslation(self):
        return {}

    def getVmPortTranslation(self, vmId):
        return VmPortTranslation(vmid=vmId)


class VmPortTranslation(object):

    def __init__(self, *args, **kwargs):
        self.vmPorts = []
        self.vmId = None

        if len(args) == 1 and isinstance(args[0], str):
            self.vmPorts = VmPortTranslation.fromString(args[0])
        else:
            for arg in args:
                if isinstance(arg, list) or isinstance(arg, tuple):
                    self.add(*arg)

        if kwargs.has_key('vmid'):
            self.vmId = kwargs['vmid']

    @staticmethod
    def fromDict(data):
        """ {vmId: [(vmPort, gwPort), ...], ...} => {vmId: [VmPortTranslation, ...], ...} """
        result = {}
        if isinstance(data, dict):
            for vmId, vmPorts in data.iteritems():
                result[vmId] = VmPortTranslation(*vmPorts, vmid=vmId)
        return result

    @staticmethod
    def fromTuple(tup):
        """ [(vmId, vmPort, gwPort), ...] ==> {vmId: [VmPortTranslation, ...], ...} """
        result = {}
        for vmId, vmPort, gwPort in tup:
            if not result.has_key(vmId):
                result[vmId] = VmPortTranslation(vmid=vmId)
            result[vmId].add(vmPort, gwPort)
        return result

    @staticmethod
    def fromString(string):
        return [tuple(ports.split(':')) for ports in string.split(',')]

    @staticmethod
    def fromStringWithVm(string):
        vmId, ports = string.split('=')
        return vmId, self.fromString(ports)

    def toString(self):
        return ','.join([':'.join(port) for port in self.vmPorts])

    def toStringWithVm(self):
        return '='.join((self.vmId, self.toString()))

    def toList(self):
        return self.vmPorts

    def toDict(self):
        return {str(self.vmId): self.toList()}

    def add(self, vmPort, gwPort):
        self.vmPorts.append((str(vmPort), str(gwPort)))

    def __len__(self):
        return len(self.vmPorts)

    def __str__(self):
        return str(self.vmPorts)

    def __repr__(self):
        return str(self.vmPorts)

    def findGwPortFromVmPort(self, port):
        for vmPort, gwPort in self.vmPorts:
            if vmPort == port:
                return gwPort
        return None

    def findVmPortFromGwPort(self, port):
        for vmPort, gwPort in self.vmPorts:
            if gwPort == port:
                return vmPort
        return None

