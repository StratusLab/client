#!/usr/bin/env python

from optparse import OptionParser

from stratuslab.CommandBase import CommandBase   
from stratuslab.configurator import Configurator

class MainProgram(CommandBase):
    '''A command-line program to configure StrtusLab.'''

    def __init__(self):
        
        self.parser = OptionParser()
        self.parser.add_option("-f", "--file", dest="filename",
                          help="write report to FILE", metavar="FILE")
        self.parser.add_option("-q", "--quiet",
                          action="store_false", dest="verbose", default=True,
                          help="don't print status messages to stdout")

        (self.options, self.args) = self.parser.parse_args()

        super(MainProgram,self).__init__()
        return


    def doWork(self):
        configurator = Configurator()
        self.logMessage('Done!')


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
