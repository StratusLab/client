#!/usr/bin/python

# ${BUILD_INFO}
# ${LEGAL}

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import ListGenerator
from stratuslab.cloud.one import OneVmState

class VmListGenerator(ListGenerator):
    
    def __init__(self):
        super(VmListGenerator,self).__init__()
        self.title = 'List of instances'
        self.fields = {'id': 'Id', 
                       'username': 'User', 
                       'deploy_id': 'Name', 
                       'state': 'Stat', 
                       'cpu': 'CPU', 
                       'memory': 'Mem', 
                       'hostname': 'Node', 
                       'ip': 'IP', 
                       'stime': 'Time'
                       }
        self.idTemplate = '            <td><a href="vmdetail.py?id=%(value)s"/>%(value)s</a></td>\n'
    
    def _getData(self):
        return self.monitor.listVms()

    def _getState(self, info):
        stateValue = info.attribs.get('state','')
        lcmStateValue = info.attribs.get('lcm_state','')
        state = OneVmState(stateValue, lcmStateValue)
        return str(state)

if __name__ == '__main__':
    VmListGenerator().run()
