#!/usr/bin/python

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import DetailedGenerator

class VmDetailGenerator(DetailedGenerator):
    
    def __init__(self):
        super(VmDetailGenerator,self).__init__()
        self.title = 'Instance detail'
        self.fieldGroups = {'VIRTUAL MACHINE INFORMATION': {'id': 'Id',
                                                            'deploy_id': 'Deployment id',
                                                            'state': 'State',
                                                            'lcm_state': 'State2',
                                                            'stime': 'Start time',
                                                            'etime': 'End time',
                                                            },
                            'VIRTUAL MACHINE MONITORING': {},
                            }
    
    def _getData(self):
        id = self._getId()
        return self.monitor.vmDetail([id])
    
if __name__ == '__main__':
    VmDetailGenerator().run()
