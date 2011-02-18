#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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

class Claudia(object):

    def __init__(self, configHolder):
        # this call makes all configuration parameters and command-line options
        # available as fields of self using the Camel case convention.
        # For example, the config parameter 'one_username' is available as self.oneUsername.
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        # add your packages here 
        #self.packages = ['apache2']
        self.packages = []

        # claudia configuration files
        self.smFile = "/root/claudiaprops/sm.properties"
        self.tcloudFile = "/root/claudiaprops/tcloud.properties"
        self.claudiaClientFile= "/root/claudiaprops/claudiaClient.properties"

        # temp global variables to be included in stratus.cfg
        self.domainName = "grnet"
        self.claudiaHome = "/opt/claudia/prueba/"

        # properties translation
        # sm.properties
        self.smprops = {"java.naming.provider.url":"tcp://"+self.frontendIp+":61616", \
                        "RestListenerHost":self.frontendIp, \
                        "SMIHost":self.frontendIp, \
                        "ImagesServerHost":self.frontendIp, \
                        "VEEMHost":self.frontendIp, \
                        "SiteRoot":self.domainName
                        # missing network configuration
                        }

        # tcloud.properties
        self.tcloudprops = {"com.telefonica.claudia.server.host":self.frontendIp, \
                            "oneUser":self.oneUsername, \
                            "onePassword":self.onePassword, \
                            "oneEnvironmentPath":self.claudiaHome+"repository/"
                            }

        # claudiaClient.properties
        self.ccprops = {"domain.root":self.domainName, \
                        "smi.host":self.frontendIp, \
                        "rest.host":self.frontendIp
                        }

    def _overrideValueInFile(self, key, value, fileName):
        # Here's how you could override config files...
        search = key + '='
        replace = key + '=' + value
        Util.appendOrReplaceInFile(fileName, search, replace)

    def run(self):
        self._installPackages()
        self._configure()
        self._startServices()
        
    def _installPackages(self):
        if self.packages:
            self.system.installPackages(self.packages)

    def _configure(self):
        # configure sm.properties file
        print " :: Configuring "+self.smFile
        for k in self.smprops:
            #print k + " |-----> " + self.smprops[k]
            self._overrideValueInFile(k, self.smprops[k], self.smFile)

        # configure tcloud.properties file
        print " :: Configuring "+self.tcloudFile
        for k in self.tcloudprops:
            #print k + " |-----> " + self.tcloudprops[k]
            self._overrideValueInFile(k, self.tcloudprops[k], self.tcloudFile)

        # configure claudiaClient.properties file
        print " :: Configuring "+self.claudiaClientFile
        for k in self.ccprops:
            #print k + " |-----> " + self.ccprops[k]
            self._overrideValueInFile(k, self.ccprops[k], self.claudiaClientFile)

    def _startServices(self):
        self.system.execute(['ls', '-l'])
        self.system.execute(['pwd'])
