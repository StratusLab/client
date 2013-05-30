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

import cgi
import json
import os
import sys

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ConfigurationException
from stratuslab.pat.Client import PortTranslationDbClient

# FIXME: Is this class actually used anywhere?
class PortTranslationService(object):
    def __init__(self, configFile=''):
        self.configFile = configFile
        configHolder = ConfigHolder(config=self._loadConfiguration())
        self.portTranslation = PortTranslationDbClient(configHolder)

    def _loadConfiguration(self):
        return ConfigHolder.configFileToDict(self._findConfigFile())

    def _findConfigFile(self):
        cgiConfig = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'conf/stratuslab.cfg')
        paths = (self.configFile, cgiConfig)
        for path in paths:
            if os.path.exists(path):
                return path
        raise(ConfigurationException('Missing configuration file'))

    def _sendJson(self, data):
        jsonData = json.dumps(data)
        print "Content-type: application/json\r\n\r\n"
        print jsonData

    def _convertPortTranslationToJson(self, cleanPorts):
        rawPorts = {}
        for vmId, vmPorts in cleanPorts.iteritems():
            rawPorts[vmId] = vmPorts.toList()
        return rawPorts

    def run(self):
        form = cgi.FieldStorage()
        vmId = form.getvalue('vmid')
        cleanPorts = self.portTranslation.getPortTranslation(vmId)
        rawPorts = self._convertPortTranslationToJson(cleanPorts)
        self._sendJson(rawPorts)

