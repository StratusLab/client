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

import json
import sqlite3

from stratuslab import Defaults
from stratuslab import Util
from stratuslab.HttpClient import HttpClient
from stratuslab.pat.Core import PortTranslation, VmPortTranslation

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
        if self.verboseLevel >= Util.VERBOSE_LEVEL_NORMAL:
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

