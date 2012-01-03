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
import commands, urllib2, time
from xml.dom.minidom import parseString

class ClaudiaEvent:

    CLAUDIA_EXEC = '/opt/claudia/bin/ClaudiaC'
    CLAUDIA_EVENTTYPE = 'agent'
    CLAUDIA_FQN = 'grnet.customers.tid.services.s1.kpis.jobqueue'
    CLAUDIA_VALUE = '100'     

    def _getStatus(self, url):
        response = urllib2.urlopen(url)
        data = response.read()

        xml = parseString(data)    
        status = xml.getElementsByTagName('Task').item(0).getAttribute('status')
        return status
    
    def sendEvent(self):
        event = '%s "event(%s,%s,%s)" 2> /dev/null' % (ClaudiaEvent.CLAUDIA_EXEC, ClaudiaEvent.CLAUDIA_EVENTTYPE, ClaudiaEvent.CLAUDIA_FQN, ClaudiaEvent.CLAUDIA_VALUE)

        output = commands.getstatusoutput(event)
        url = output[1]
        return url
#        status = self._getStatus(url)
    
#        while(status == "running"):
#            time.sleep(1)
#            status = self._getStatus(url)
    
#        self.assertEquals(status, "success")

if __name__ == "__main__":
    unittest.main()
