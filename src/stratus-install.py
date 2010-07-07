#!/usr/bin/env python

import os
import sys
from optparse import OptionParser

from stratuslab.CommandBase import CommandBase   
from stratuslab.Installator import Installator

class MainProgram(CommandBase):
    '''A command-line program to install StratusLab front-end.'''

    def __init__(self):
        self.dirPath =  os.path.abspath(os.path.dirname(__file__))
        usage = 'usage: %prog [options]'
        parser = OptionParser(usage=usage)

        parser.add_option('-c', '--config', dest='configFile',
                help='configuration file', metavar='FILE',
                default='%s/stratuslab.cfg.user' % self.dirPath)
        parser.add_option('-t', '--template', dest='onedTpl',
                help='ONe daemon template', metavar='TEMPLATE',
                default='%s/oned.conf.tpl' % self.dirPath)
        parser.add_option('-n', '--node', dest='nodeAddr',
                help='IP address or hostname of the node to configure',
                default=None, metavar='ADDRESS')
        parser.add_option('--im', dest='infoDriver',
                help='information driver', metavar='IM_NAME',
                default='im_stratuslab')
        parser.add_option('--vmm', dest='virtDriver',
                help='virtualization driver', metavar='VM_NAME',
                default='vm_stratuslab')
        # TODO: take care of this for the node deps installation/config
        parser.add_option('--tm', dest='transfertDriver',
                help='transfert driver', metavar='VM_NAME',
                default='tm_stratuslab')
        parser.add_option('-k', '--private-key', dest='privateKey',
                help='private key for ssh node connection', metavar='FILENAME',
                default=None)
        parser.add_option('-q', '--quiet', dest='quiet',
                help='don\'t print status messages to stdout',
                default=False, action='store_true')
        parser.add_option('-v', action='store_true', dest='verbose', 
                help='display more informations', default=False)

        (self.options, self.args) = parser.parse_args()

        super(MainProgram, self).__init__()

    def doWorkNodes(self):
      	installator = Installator(self.options) 
        installator.propagateNodeInfos()

        if installator.checkConnectivity(self.options.nodeAddr) > 0: 
            raise ValueError('Unable to connect the node %s' %
                self.options.nodeAddr)

        installator.createONeAdmin(installator.node)
        installator.installNodeDependencies()
        installator.setupFileSharingClient()
        installator.configureFileSharingClient()
        installator.addONeNode()

    def doWorkFrontend(self):
      	installator = Installator(self.options) 
        installator.createONeAdmin(installator.frontend)
        installator.configureONeAdmin()
        installator.installONe()
        installator.configureONeDaemon()
        installator.setupFileSharingServer()
        installator.startONeDaemon()

    def doWork(self):
        if self.options.nodeAddr is not None:
            self.doWorkNodes() 
        else:
            self.doWorkFrontend()


if __name__ == '__main__':
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'

