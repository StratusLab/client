#!/usr/bin/python

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import DetailedGenerator

class NodeDetailGenerator(DetailedGenerator):
    
    def __init__(self):
        super(NodeDetailGenerator,self).__init__()
        self.title = 'Node detail'
        self.fieldGroups = {'Host Information': {'id': 'Id', 
                                                 'name': 'Name', 
                                                 'state': 'State', 
                                                 'im_mad': 'im_mad', 
                                                 'vm_mad': 'vm_mad', 
                                                 'tm_mad': 'tm_mad'},
                            'Host Shares': {'totalmemory': 'Max mem',
                                            'usedmemory': 'Used mem (real)', 
                                            'mem_usage': 'Used mem (allocated)', 
                                            'max_cpu': 'Max CPU',
                                            'used_cpu': 'Used CPU (real)', 
                                            'cpu_usage': 'Used CPU (allocated)', 
                                            'running_vms': 'Running VMs'},
                            'Monitoring Information': {'arch': 'Arch', 
                                                       'cpuspeed': 'CPU speed', 
                                                       'freecpu': 'Free CPU', 
                                                       'free_mem': 'Free mem', 
                                                       'hostname': 'Hostname', 
                                                       'hypervisor': 'Hypervisor', 
                                                       'modelname': 'Model', 
                                                       'netrx': 'Netrx', 
                                                       'nettx': 'Nnettx', 
                                                       'totalcpu': 'Total CPU', 
                                                       'totalmemory': 'Total mem', 
                                                       'usedcpu': 'Used CPU', 
                                                       'usedmemory': 'Used mem'}
                            }
    
    def _getData(self):
        id = self._getId()
        return self.monitor.nodeDetail([id])
    
if __name__ == '__main__':
    NodeDetailGenerator().run()
