#!/usr/bin/python

# ${BUILD_INFO}
# ${LEGAL}

import cgi
import cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import ListGenerator
from stratuslab.cloud.one import OneHostState

class NodeListGenerator(ListGenerator):
    
    def __init__(self):
        super(NodeListGenerator,self).__init__()
        self.title = 'List of nodes'
        self.template = open('list.html.tpl').read()
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
    NodeListGenerator().run()
