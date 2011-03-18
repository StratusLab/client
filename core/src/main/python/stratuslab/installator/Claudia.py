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
from hashlib import sha1
from time import sleep

class Claudia(object):

    def __init__(self, configHolder):
        # this call makes all configuration parameters and command-line options
        # available as fields of self using the Camel case convention.
        # For example, the config parameter 'one_username' is available as self.oneUsername.
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        # add your packages here 
        #self.packages = ['apache2']
        self.packages = ['claudia-client-rpm', 'clotho-rpm', 'tcloud-server-rpm', 'activemq']
        
        # claudia configuration files
        self.smFile = self.claudiaHome+"/conf/sm.properties"
        self.tcloudFile = self.claudiaHome+"/conf/tcloud.properties"
        self.claudiaClientFile= self.claudiaHome+"/conf/claudiaClient.properties"

        # Network configuration 
        self.publicNet = "IP:"+self.claudiaPublicIp+";"+    \
                         " Netmask:"+self.claudiaPublicNetmask+";"+  \
                         " Gateway:"+self.claudiaPublicGateway+\
                         "; DNS:"+self.claudiaPublicDns+";"+  \
                         " Public:yes;"
        if self.claudiaPublicNetwork:
            self.publicNet = "Network:"+self.claudiaPublicNetwork+"; "+self.publicNet


        self.privateNet = "IP:"+self.claudiaPrivateIp+";"+               \
                          " Netmask:"+self.claudiaPrivateNetmask+";"+     \
                          " Gateway:"+self.claudiaPrivateGateway+";"+     \
                          " DNS:"+self.claudiaPrivateDns+";"+             \
                          " Public:no;"
        if self.claudiaPrivateNetwork:
            self.privateNet = "Network:"+self.claudiaPrivateNetwork+"; "+self.privateNet

        self.network="[ "+self.publicNet+" ], [ "+self.privateNet+" ]"

        # properties translation
        # sm.properties
        self.smprops = {"java.naming.provider.url":"tcp://"+self.frontendIp+":61616", \
                        "RestListenerHost":self.frontendIp, \
                        "SMIHost":self.frontendIp, \
                        "ImagesServerHost":self.frontendIp, \
                        "VEEMHost":self.frontendIp, \
                        "SiteRoot":self.domainName, \
                        "NetworkRanges":self.network
                        }

        #pass the password to the sha1 constructor 
        self.createSha1 = hashlib.sha1(self.onePassword)
 
        #dump the password out in text 
        self.sha1Password = self.createSha1.hexdigest()
        #print "Password en sha1: "+self.sha1Password

        # tcloud.properties
        self.tcloudprops = {"com.telefonica.claudia.server.host":self.frontendIp, \
                            "oneUser":self.oneUsername, \
                            "onePassword":self.sha1Password, \
                            "oneEnvironmentPath":self.claudiaHome+"repository/", \
                            "oneNetworkBridge":self.nodeBridgeName
                            }

        # claudiaClient.properties
        self.ccprops = {"domain.root":self.domainName, \
                        "smi.host":"http://"+self.frontendIp+":", \
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
            print " :: Installing packages: "
            for p in self.packages:
                print " ::\t"+p
            print " ::"
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
        print " ::"

    def _startServices(self):
        print " :: Starting activemq"
        self.system.execute(['/etc/init.d/activemq', 'restart'])
        # Wait 10 seconds for giving time to activemq to completely start
        time.sleep(10)
        
        print " :: Starting tcloud"
        self.system.execute(['/etc/init.d/tcloudd', 'restart'])
        
        print " :: Starting clotho"
        self.system.execute(['/etc/init.d/clothod', 'restart'])
        print " ::"
