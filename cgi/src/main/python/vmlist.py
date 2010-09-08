#!/usr/bin/python

# ${BUILD_INFO}
# ${LEGAL}

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import ListGenerator

class VmListGenerator(ListGenerator):
    
    def __init__(self):
        super(VmListGenerator,self).__init__()
        self.title = 'List of instances'
        self.fields = {'id': 'Id', 
                       'username': 'User', 
                       'deploy_id': 'Name', 
                       'state': 'Stat', 
                       'lcm_state': 'Stat2', 
                       'cpu': 'CPU', 
                       'memory': 'Mem', 
                       'hostname': 'Node', 
                       'ip': 'IP', 
                       'stime': 'Time'
                       }
        self.idTemplate = '            <td><a href="vmdetail.py?id=%(value)s"/>%(value)s</a></td>\n'
    
    def _getData(self):
        return self.monitor.listVms()

if __name__ == '__main__':
    VmListGenerator().run()
