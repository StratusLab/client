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
import unittest, commands, urllib
from xml.dom.minidom import parseString

class ClaudiaTest(unittest.TestCase):

    def testDeploy(self):
        deploy = '/opt/claudia/bin/ClaudiaC "deploy(tid,stid1,http://84.21.173.141:8080/telefonica.xml)" 2> /dev/null'
        #print deploy + "\n"
    
        output = commands.getstatusoutput(deploy)
        url = output[1]
        #print url + "\n"
    
        req = urllib.urlopen(url)
        data = req.read()
        #print data + "\n"

        xml = parseString(data)    
        status = xml.getElementsByTagName('Task').item(0).getAttribute('status')
        #print status + "\n"
        
        if(status == "success" or status == "running"):
            check = "OK"
        else:
            check = status
    
        #print check

        self.assertEquals(check, "OK")

if __name__ == "__main__":
    unittest.main()
