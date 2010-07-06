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
        self.parser = OptionParser(usage=usage)

        self.parser.add_option('-c', '--config', dest='configFile',
                help='configuration file', metavar='FILE',
                default='%s/stratuslab.cfg.user' % self.dirPath)
        self.parser.add_option('-q', '--quiet', action='store_false', 
                dest='verbose', default=True,
                help='don\'t print status messages to stdout')
        self.parser.add_option('-v', action='store_true', dest='verbose', 
                default=False, help='display more informations')

        (self.options, self.args) = self.parser.parse_args()

        super(MainProgram, self).__init__()

    def doWork(self):
      	installator = Installator(self.options.configFile) 
        installator.setupONeAdmin()
        installator.installONe()
        installator.setupONeEnv()
        self.logMessage('Done!')


if __name__ == '__main__':
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'

