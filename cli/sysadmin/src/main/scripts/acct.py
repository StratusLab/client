#!/usr/bin/python

import sys
import os
import operator
import xml.etree.ElementTree as ET
import commands
import urllib2
import datetime

from optparse import OptionParser

from stratuslab.accounting.Computer import Computer

class MainProgram():
    '''A command-line program to extract accounting data from StratusLab.'''

    def __init__(self, argv=None):
        self.lastNoOfHours = None
        self.outputDir = None
        self.parser = OptionParser()
        self.parse()
        self.do_work()

    def parse(self):
        usage = '''usage: %prog <last-no-of-hours>

<last-no-of-hours>  Number of hours from when to calculate accounting data for each user.'''

        self.parser.add_option('-d', '--output-dir', dest='outputDir',
                               help='Directory in which to generate the accounting files. Default to local directory.',
                               default='.')

        self.parser.usage = usage
        self.options, self.args = self.parser.parse_args()
        self._check_args()

    def _check_args(self):
        if len(self.args) > 1:
            self.usage_exit_too_many_arguments()
        if len(self.args) < 1:
            self.usage_exit_too_few_arguments()
        try:
            self.lastNoOfHours = int(self.args[0])
        except:
            print "invalid <last-no-of-hours> format"
            self._exit(2)
    if self.lastNoOfHours > 24:
        print "Invalid <last-no-of-hours>, cannot be more than 24"
        if self.lastNoOfHours < 1:
            print "Invalid <last-no-of-hours>, cannot be less than 1"
        self.outputDir = self.options.outputDir

    def usage_exit_too_many_arguments(self):
        self.usage_exit("Too many arguments")

    def usage_exit_too_few_arguments(self):
        self.usage_exit("Too few arguments")

    def usage_exit(self, msg=None):
        if msg:
            print msg, '\n'
        self.parser.print_help()

        self._exit(1)

    def _exit(self, code):
        sys.exit(code)

    def do_work(self):
        refDate = datetime.datetime(1970,1,1)
        now = datetime.datetime.now()
        delta = datetime.timedelta(hours=self.lastNoOfHours)

        fromInSecs = self.total_seconds(now - delta - refDate)
        toInSecs = self.total_seconds(now - refDate)

    if self.lastNoOfHours == 24:
        daily = True
    else:
        daily = False
        Computer(fromInSecs, toInSecs, self.outputDir, daily).compute()

    def total_seconds(self, td):
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

main = MainProgram

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
