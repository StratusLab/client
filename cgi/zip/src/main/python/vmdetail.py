#!/usr/bin/python

# ${BUILD_INFO}
# ${LEGAL}

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import DetailedGenerator
from stratuslab.cloud.one import OneVmState

class VmDetailGenerator(DetailedGenerator):
    
    def __init__(self):
        super(VmDetailGenerator,self).__init__()
        self.title = 'Instance detail'
        self.fieldGroups = {'Virtual Machine Information': {'id': 'Id',
                                                            'deploy_id': 'Deployment id',
                                                            'state': 'State',
                                                            'lcm_state': 'State2',
                                                            'stime': 'Start time',
                                                            'etime': 'End time',
                                                            },
                            'Virtual Machine Monitoring': {},
                            }
    
    def _getData(self):
        id = self._getId()
        return self.monitor.vmDetail([id])
    
    def _getState(self, info):
        stateValue = info.attribs.get('state','')
        lcmStateValue = info.attribs.get('lcm_state','')
        state = OneVmState(stateValue, lcmStateValue)
        return str(state)

if __name__ == '__main__':
    VmDetailGenerator().run()
