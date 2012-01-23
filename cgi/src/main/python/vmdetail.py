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
from stratuslab.web.Generator import DetailedGenerator
from stratuslab.cloud.one import OneVmState

class VmDetailGenerator(DetailedGenerator):
    
    def __init__(self, configFile):
        super(VmDetailGenerator, self).__init__(configFile)
        self.title = 'Instance detail'
        self.fieldGroups = [['Virtual Machine Information', [['id', 'Id'],
                                                             ['deploy_id', 'Deployment id'],
                                                             ['state', 'State'],
                                                             ['stime', 'Start time'],
                                                             ['etime', 'End time'],
                                                             ['history_hostname', 'Node'],
                                                             ['template_context_public_key', 'PubKey'],
                                                             ['template_cpu', 'vCPUs'],
                                                             ['memory', 'Memory'],
                                                             ['template_nic_ip', 'IP'],
                                                             ['template_nic_network', 'Network'],
                                                             ['template_disk_source', 'Disk Source'],
                                                             ['template_disk_size', 'Disk Size'],
                                                             ['template_disk_driver', 'Disk Driver'],
                                                             ['template_disk_save', 'Save Disk'],
                                                             ]
        
                            ],
                            ['Virtual Machine Monitoring', [['cpu', 'CPU'],
                                                            ['net_rx', 'Net RX'],
                                                            ['net_tx', 'Net TX'],
                                                            ]]
                           ]

        configHolder = ConfigHolder(config=self._loadConfiguration())
        configHolder.assign(self)
        if Util.isTrueConfVal(self.patEnable):
            self.fieldGroups[0].append(['template_pat', 'PAT (VM:GW)'])
    
    def _getData(self):
        id = self._getId()
        return self.monitor.vmDetail([id])

    def _getState(self, info):
        stateValue = info.attribs.get('state','')
        lcmStateValue = info.attribs.get('lcm_state','')
        state = OneVmState(stateValue, lcmStateValue)
        return str(state)

if __name__ == '__main__':
    configFile = ''
    if (len(sys.argv) > 1):
        configFile = sys.argv[1]
        VmDetailGenerator._getQueryValue = lambda _m, id: sys.argv[2]
    VmDetailGenerator(configFile).run()
