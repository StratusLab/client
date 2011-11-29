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
import time

class Monitoring(object):

    def __init__(self, configHolder):     
        # this call makes all configuration parameters and command-line options
        # available as fields of self using the Camel case convention.
        # For example, the config parameter 'one_username' is available as self.oneUsername.
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        
        # add your packages here 
        self.packages = ['collectd-base', 'collectd-basicprobes', 'collectd-java',
                         'collectd-api-rpm', 'collectd-collector-rpm', 'collectd-extendedprobes-rpm','']
       
        #pass the password to the sha1 constructor 
        self.createSha1 = hashlib.sha1(self.onePassword)
 
        #dump the password out in text 
        self.sha1Password = self.createSha1.hexdigest()
        #print "Password en sha1: "+self.sha1Password
        
        #monitoring probes properties        
        self.monitoringprops = {"mysqlurl":self.monitoringMysqlurl, \
                            "mysqluser":self.monitoringMysqluser, \
                            "mysqlpassword":self.monitoringMysqlpassword, \
                            "persistence.jars":self.monitoringPersistenceJars
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
        #print " :: Configuring "+self.smFile
        for k in self.monitoringprops:
            print k + " |-----> " + self.monitoringprops[k]
            self._overrideValueInFile(k, self.monitoringprops[k], self.monitoringProperites)
                
        print " ::"
    
    def _startServices(self):
        print " :: Starting collectd"
        self.system.execute(['/etc/init.d/collectd', 'restart'])
        # Wait 10 seconds for giving time to activemq to completely start
        #time.sleep(10)
        
        # last line
        print " ::"
