#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, CNRS/IBCP
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

import json
import sqlite3
import sys

from stratuslab import Defaults
from stratuslab import Util
from stratuslab.CommandBase import CommandBaseUser
from stratuslab.HttpClient import HttpClient

etree = Util.importETree()


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

    def __getitem__(self, key):
        return Layers(self.vmPorts[key])

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


class PortTranslationCommand(CommandBaseUser):
    @staticmethod
    def addAllOptions(parser):
        PortTranslationCommand.addCommonOptions(parser)
        PortTranslationCommand.addAdvancedOptions(parser)

    @staticmethod
    def addCommonOptions(parser):
        parser.add_option('--pat-enable', dest='patEnable',
                help='show port address translations',
                action='store_true', default=False)

        parser.add_option('--pat-service-host', dest='patServiceHost',
                help='set the hostname/ip of port translation service',
                action='store', metavar='HOST/IP')

        parser.add_option('--pat-gateway-host', dest='patGatewayHost',
                help='set the hostname/ip of port translation gateway',
                action='store', metavar='HOST/IP')

    def checkCommonOptions(self):
        self.checkServiceHost()
        self.checkGatewayHost()

    def checkServiceHost(self):
        self._setOptionIfNotDefined('patServiceHost', self.options.endpoint)

    def checkGatewayHost(self):
        self._setOptionIfNotDefined('patGatewayHost', self.options.endpoint)

    def _setOptionIfNotDefined(self, option, default):
        if not getattr(self.options, option, None):
            if self.verboseLevel >= Util.NORMAL_VERBOSE_LEVEL:
                sys.stdout.write("Warning: '%s' is not defined, using '%s'.\n" % (option, default))
            setattr(self.options, option, default)


class PortTranslation(object):
    def __init__(self, configHolder):
        self.verboseLevel = 0
        configHolder.assign(self)

    def isTranslatedNetwork(self, network):
        return Util.isTrueConfVal(self.patEnable) and network in self.patNetworks

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


class PortTranslationWebClient(PortTranslation):
    def __init__(self, configHolder):
        self.client = HttpClient(configHolder)
        self.patServiceHost = None
        super(PortTranslationWebClient, self).__init__(configHolder)

    def getAllPortTranslation(self):
        return self.getPortTranslation()

    def getVmPortTranslation(self, vmId):
        ports = self.getPortTranslation(vmId)
        return ports.get(vmId, VmPortTranslation(vmid=vmId))

    def getPortTranslation(self, vmId=None):
        url = self._buildUrl(vmId)
        ports = self._getAndCleanJson(url)
        return ports

    def _buildUrl(self, vmId=None):
        url = "http://%s/cgi-bin/vmports.py" % self.patServiceHost
        if vmId:
            url = url + "?vmid=%s" % vmId
        return url

    def _getAndCleanJson(self, url):
        try:
            headers, content = self._getJson(url)
            ports = json.loads(content, object_hook=VmPortTranslation.fromDict)
        except Exception, e:
            self._handleException(e)
        return ports

    def _getJson(self, url):
        headers, content = self.client.get(url, accept='application/json')
        return headers, content.replace('\\', '')

    def _handleException(self, exception):
        if self.verboseLevel >= Util.NORMAL_VERBOSE_LEVEL:
            raise exception
        else:
            raise Exception("Couldn't get port translation. Increase verbose level to see details.")


class PortTranslationDbClient(PortTranslation):
    def __init__(self, configHolder):
        super(PortTranslationDbClient, self).__init__(configHolder)

        self.conn = sqlite3.connect(self.patServiceDbname or Defaults.patServiceDbname)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def getAllPortTranslation(self):
        return self.getPortTranslation()

    def getVmPortTranslation(self, vmId):
        ports = self.getPortTranslation(vmId)
        return ports.get(vmId, VmPortTranslation(vmid=vmId))

    def getPortTranslation(self, vmId=None):
        query = self._buildQuery(vmId)
        rawPorts = self._executeQuery(query)
        return VmPortTranslation.fromTuple(rawPorts)

    def getAllGwPorts(self):
        query = "SELECT DISTINCT(local) FROM ports"
        rawPorts = self._executeQuery(query)
        formatedPorts = [port for port, in rawPorts]
        return formatedPorts

    def getGwPortFromVmPort(self, vmId, vmPort):
        query = "SELECT * FROM ports WHERE id = '%s' AND remote = '%s'" % (vmId, vmPort)
        return self._fetchSingleValue(query, 'local')

    def getVmPortFromGwPort(self, vmId, gwPort):
        query = "SELECT * FROM ports WHERE id = '%s' AND local = '%s'" % (vmId, gwPort)
        return self._fetchSingleValue(query, 'remote')

    def _buildQuery(self, vmId):
        query = "SELECT id, remote, local FROM ports"
        if vmId:
            query = query + " WHERE id = '%d'" % int(vmId)
        return query

    def _executeQuery(self, query):
        self.cursor.execute(query)
        rawData = self.cursor.fetchall()
        return rawData

    def _fetchSingleValue(self, query, field):
        self.cursor.execute(query)
        row = self.cursor.fetchone()
        if not row:
            return None
        return row[field]

