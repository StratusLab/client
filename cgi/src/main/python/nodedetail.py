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
from stratuslab.cloud.one import OneHostState

class NodeDetailGenerator(DetailedGenerator):
    
    def __init__(self, configFile):
        super(NodeDetailGenerator, self).__init__()
        self.title = 'Node detail'
        self.fieldGroups = [['Host Information', [['id', 'Id'],
                                                  ['name', 'Name'],
                                                  ['state', 'State'],
                                                  ['im_mad', 'im_mad'],
                                                  ['vm_mad', 'vm_mad'],
                                                  ['tm_mad', 'tm_mad']]],
                            ['Host Shares', [['host_share_max_mem', 'Max mem'],
                                             ['host_share_used_mem', 'Used mem (real)'], 
                                             ['host_share_mem_usage', 'Used mem (allocated)'], 
                                             ['host_share_max_cpu', 'Max CPU'],
                                             ['host_share_used_cpu', 'Used CPU (real)'], 
                                             ['host_share_cpu_usage', 'Used CPU (allocated)'], 
                                             ['host_share_running_vms', 'Running VMs']]],
                            ['Monitoring Information', [['template_arch', 'Arch'], 
                                                        ['template_cpuspeed', 'CPU speed'], 
                                                        ['template_freecpu', 'Free CPU'], 
                                                        ['template_free_mem', 'Free mem'], 
                                                        ['template_hostname', 'Hostname'], 
                                                        ['template_hypervisor', 'Hypervisor'], 
                                                        ['template_modelname', 'Model'], 
                                                        ['template_netrx', 'Netrx'], 
                                                        ['template_nettx', 'Nnettx'], 
                                                        ['template_totalcpu', 'Total CPU'], 
                                                        ['template_totalmemory', 'Total mem'], 
                                                        ['template_usedcpu', 'Used CPU'], 
                                                        ['template_usedmemory', 'Used mem'],
                                                        ['template_disk_free', 'Used Disk'],
                                                        ]]
                            ]
    
    def _getData(self):
        id = self._getId()
        return self.monitor.nodeDetail([id])

    def _getState(self, info):
        stateValue = info.attribs.get('state','')
        state = OneHostState(stateValue)
        return str(state)

if __name__ == '__main__':
    configFile = ''
    if (len(sys.argv) > 1):
        configFile = sys.argv[1]
        NodeDetailGenerator._getQueryValue = lambda _m, id: sys.argv[2]
    NodeDetailGenerator(configFile).run()
