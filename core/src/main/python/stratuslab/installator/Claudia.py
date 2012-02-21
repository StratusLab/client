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

import stratuslab.Util as Util
import stratuslab.system.SystemFactory as SystemFactory
import hashlib
from stratuslab.Util import printStep, restartService, sleep
from stratuslab.installator.Installator import Installator

class Claudia(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['claudia-common-rpm', 'claudia-client-rpm', 'clotho-rpm',
                         'tcloud-server-rpm', 'activemq', 'reportclient-rpm']
        
        self._setClaudiaConfigFiles()
        self._setPublicNetwork()
        self._setPrivateNetwork()
        self._setNetwork()
        self._dumpOnePassword()
        self._retrieveOneVersion()
        self._setSMProperties()
        self._setTCloudProperties()
        self._setClaudiaClientProperties()
        self._setReportProperties()

    def _installFrontend(self):
        printStep('Installing packages')
        self.system.installPackages(self.packages)

    def _setupFrontend(self):
        self.setup(self.smFile, self.smProperties)
        self.setup(self.tcloudFile, self.tCloudProperties)
        self.setup(self.claudiaClientFile, self.claudiaClientProperties)
        self.setup(self.reportClientFile, self.reportProperties)

    def _startServicesFrontend(self):
        restartService('activemq')
        sleep(10)
        restartService('tcloudd')
        restartService('clothod')

    def _overrideValueInFile(self, key, value, fileName):
        search = key + '='
        replace = key + '=' + value
        Util.appendOrReplaceInFile(fileName, search, replace)

    def _retrieveOneVersion(self):
        if not hasattr(self, 'oneVersion') or not self.oneVersion:
            self.oneVersion = '2.2'
                        
    def _dumpOnePassword(self):
        createSha1 = hashlib.sha1(self.onePassword)
        self.onePassword = createSha1.hexdigest()
    
    def _setTCloudProperties(self):
        self.tCloudProperties = {"com.telefonica.claudia.server.host": self.frontendIp,
                                 "oneUser": self.oneUsername,
                                 "onePassword": self.onePassword,
                                 "oneEnvironmentPath": self.claudiaHome + "repository/",
                                 "oneNetworkBridge": self.nodeBridgeName,
                                 "ONEVERSION": self.oneVersion }
    
    def _setClaudiaClientProperties(self):
        self.claudiaClientProperties = {"domain.root": self.domainName,
                                        "smi.host": "http://" + self.frontendIp + ":",
                                        "rest.host": self.frontendIp }
        
    def _setReportProperties(self):
        self.reportProperties = {"SiteRoot": self.domainName,
                                 "TServer.url": "http://" + self.frontendIp + ":8182",
                                 "vmMonName": self.claudiaMonitorVmName,
                                 "monitorName": self.claudiaMonitorName }                    
    
    def _setSMProperties(self):
        self.smProperties = {"java.naming.provider.url":"tcp://" + self.frontendIp + ":61616", 
                            "RestListenerHost":self.frontendIp, 
                            "SMIHost":self.frontendIp,
                            "MonitoringAddress":self.frontendIp,
                            "ImagesServerHost":self.frontendIp,
                            "VEEMHost":self.frontendIp,
                            "SiteRoot":self.domainName,
                            "NetworkRanges":self.network,
                            "MacEnabled":self.claudiaMacEnabled,
                            "NetworkMacList":self.claudiaMacList,
                            "StaticIpList":self.claudiaStaticIpList }

    def _setClaudiaConfigFiles(self):
        self.smFile = self.claudiaHome + "/conf/sm.properties"
        self.tcloudFile = self.claudiaHome + "/conf/tcloud.properties"
        self.claudiaClientFile = self.claudiaHome + "/conf/claudiaClient.properties"
        self.reportClientFile = self.claudiaHome + "/conf/reportClient.properties"
    
    def _setPublicNetwork(self):
        self.publicNet = 'IP:%s; Netmask:%s; Gateway:%s; DNS:%s; Public:yes;' % (
                 self.claudiaPublicIp, 
                 self.claudiaPublicNetmask,
                 self.claudiaPublicGateway,
                 self.claudiaPublicDns)
        if self.claudiaPublicNetwork:
            self.publicNet = "Network:" + self.claudiaPublicNetwork + "; " + self.publicNet

    def _setPrivateNetwork(self):
        self.privateNet = 'IP:%s; Netmask:%s; Gateway:%s; DNS:%s; Public:yes;' % (
                 self.claudiaPrivateIp, 
                 self.claudiaPrivateNetmask,
                 self.claudiaPrivateGateway,
                 self.claudiaPrivateDns)
        if self.claudiaPrivateNetwork:
            self.privateNet = "Network:" + self.claudiaPrivateNetwork + "; " + self.privateNet
            
    def _setNetwork(self):
        self.network = "[ " + self.publicNet + " ], [ " + self.privateNet + " ]"
    
    def _configureFile(self, configFile, properties):
        printStep('Configuring %s' % configFile)
        for key, value in properties.items():
            self._overrideValueInFile(key, value, configFile)

