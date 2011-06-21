#!/usr/bin/python
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
# ${BUILD_INFO}

import sys
import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import ListGenerator
from stratuslab.cloud.one import OneVmState

class VmListGenerator(ListGenerator):
    
    def __init__(self, configFile):
        super(VmListGenerator, self).__init__()
        self.title = 'List of instances'
        self.fields = [['id', 'Id'],
                       ['username', 'User'],
                       ['name', 'Name'],
                       ['state', 'Stat'],
                       ['cpu', 'CPU'],
                       ['memory', 'Mem'],
                       ['history_hostname', 'Node'],
                       ['template_nic_ip', 'IP'],
                       ['stime', 'Time']]
        self.idTemplate = '            <td><a href="vmdetail.py?id=%(value)s"/>%(value)s</a></td>\n'
    
    def _getData(self):
        return self.monitor.listVms(showVmsFromAllUsers=True)

    def _getState(self, info):
        stateValue = info.attribs.get('state','')
        lcmStateValue = info.attribs.get('lcm_state','')
        state = OneVmState(stateValue, lcmStateValue)
        return str(state)

if __name__ == '__main__':
    configFile = ''
    if (len(sys.argv) > 1):
        configFile = sys.argv[1]
    VmListGenerator(configFile).run()

