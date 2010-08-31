#!/usr/bin/python

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util
from stratuslab.web.Generator import ListGenerator

class NodeListGenerator(ListGenerator):
    
    def __init__(self):
        super(NodeListGenerator,self).__init__()
        self.title = 'List of nodes'
        self.template = open('list.html.tpl').read()
        self.idTemplate = '            <td><a href="nodedetail.py?id=%(value)s"/>%(value)s</a></td>\n'
        self.fields = {'id':'Id', 
                       'name': 'IP', 
                       'totalcpu': 'Total CPU', 
                       'freecpu': 'Free CPU', 
                       'totalmemory': 'Total mem', 
                       'freememory': 'Free mem', 
                       'state': 'State'}
    
    def _getData(self):
        return self.monitor.listNodes()

if __name__ == '__main__':
    NodeListGenerator().run()
