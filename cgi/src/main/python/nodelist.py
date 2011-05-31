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
import cgi
import cgitb
cgitb.enable()

from stratuslab.web.Generator import ListGenerator
from stratuslab.cloud.one import OneHostState

class NodeListGenerator(ListGenerator):

    def __init__(self, configFile):
        super(NodeListGenerator, self).__init__(configFile)
        self.title = 'List of nodes'
        self.idTemplate = '            <td><a href="nodedetail.py?id=%(value)s"/>%(value)s</a></td>\n'
        self.fields = [['id','Id'],
                       ['name', 'IP'],
                       ['max_cpu', 'Total CPU'],
                       ['free_cpu', 'Free CPU'],
                       ['max_mem', 'Total mem'],
                       ['free_mem', 'Free mem'],
                       ['running_vms', 'Running VMs'],
                       ['state', 'State']]

    def _getData(self):
        return self.monitor.listNodes()

    def _getState(self, info):
        stateValue = info.attribs.get('state','')
        state = OneHostState(stateValue)
        return str(state)

if __name__ == '__main__':
    configFile = ''
    if (len(sys.argv) > 1):
        configFile = sys.argv[1]
    NodeListGenerator(configFile).run()
