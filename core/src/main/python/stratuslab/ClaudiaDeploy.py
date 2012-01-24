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
import  commands, urllib2, time
from xml.dom.minidom import parseString

class ClaudiaDeploy:

    OVF = 'file:///opt/claudia/extraFiles/glitesiteovf.xml'
    CLAUDIA_EXEC = '/opt/claudia/bin/ClaudiaC'
    CLAUDIA_SERVICENAME = 's1'
    CLAUDIA_CUSTOMER = 'tid'
    
    #def __init__(self):
    #    pass
    
    def _getStatus(self, url):
        response = urllib2.urlopen(url)
        data = response.read()

        xml = parseString(data)    
        status = xml.getElementsByTagName('Task').item(0).getAttribute('status')
        return status
    
    def doDeploy(self):
        deploy = '%s "deploy(%s,%s,%s)" 2> /dev/null' % (ClaudiaDeploy.CLAUDIA_EXEC, ClaudiaDeploy.CLAUDIA_CUSTOMER, ClaudiaDeploy.CLAUDIA_SERVICENAME, ClaudiaDeploy.OVF)

        output = commands.getstatusoutput(deploy)
        url = output[1]
    
        status = self._getStatus(url)
    
        while(status == "running"):
            time.sleep(1)
            status = self._getStatus(url)
    
        #self.assertEquals(status, "success")
        return status

if __name__ == "__main__":
    pass