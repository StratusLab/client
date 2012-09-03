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
from stratuslab.Authn import LocalhostCredentialsConnector
from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import printWarning
from stratuslab.system import SystemFactory
from stratuslab import Defaults

class OpenNebulaCommon(object):
    
    def __init__(self, configHolder):
        self.frontendIp = ''
        self.config = configHolder.config.copy()
        self.configHolder = configHolder
        configHolder.assign(self)

        self._setCloud()
        self.shareType = Defaults.SHARE_TYPE
        
    def _setCloud(self):
        self.username = self.oneUsername
        self.password = self.onePassword
        credentials = LocalhostCredentialsConnector(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.configHolder.assign(self.cloud)
        self.cloud.setEndpoint('localhost')
        
    def _createCloudAdmin(self, system):
        system.createCloudGroup(self.oneGroup, self.oneGid)
        system.createCloudAdmin()
        
    def _assignDrivers(self):
        self.infoDriver = (True and self.infoDriver) or ('im_%s' % self.hypervisor)
        self.virtDriver = (True and self.virtDriver) or ('vmm_%s' % self.hypervisor)
        self.transfertDriver = (True and self.transfertDriver) or ('tm_%s' % self.shareType)
        
    def _removeCloudNode(self, nodeId):
        self.cloud.hostRemove(nodeId)
        