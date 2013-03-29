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
from stratuslab.installator.OpenNebulaCommon import OpenNebulaCommon
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Monitor import Monitor
from stratuslab.Exceptions import InputException
from stratuslab.Authn import AuthnFactory

class Registrar(OpenNebulaCommon):

    def __init__(self, configHolder):
        self.configHolder = configHolder
        self.config = configHolder.config
        self.deRegister = False
        configHolder.assign(self)
        self.username = 'oneadmin'
        
        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.cloud.setEndpointFromParts(self.frontendIp,
                                        self.proxyPort)        

        self._assignDrivers()

    def register(self, hostnames):
        
        id = None
        for hostname in hostnames:
            if self.deRegister:
                self.deregister(hostname)
            else:
                id = self._register(hostname)
        return id

    def deregister(self, hostname):
        try:
            id = int(hostname)
        except:
            id = self._getHostnameId(hostname)
        self._removeCloudNode(id)

    def _getHostnameId(self, hostname):
        monitor = Monitor(self.configHolder)
        infoList = monitor.listNodes()
        info = None
        for i in infoList:
            if i.name == hostname:
                info = i
                break
        if not info:
            raise InputException('Failed to find node with hostname %s' % hostname)
        return int(info.id)
        

    def _register(self, hostname):
        
        self.nodeAddr = hostname
        return self._addCloudNode()
        
