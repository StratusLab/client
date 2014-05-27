#!/usr/bin/python

import sys
import os
import operator
import xml.etree.ElementTree as ET
import commands
import urllib2
import datetime
import time

from optparse import OptionParser

sys.path.append('/var/lib/stratuslab/python')

from acct.Computer import Computer

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

class MainProgram():
    '''A command-line program to extract accounting data from StratusLab.'''

    def __init__(self, argv=None):
        self.lastNoOfHours = None
        self.output_dir = None
        self.user_names = []
        self.options = None
        self.parser = OptionParser()
        self.parse()
        self.do_work()

    def parse(self):
        usage = '''usage: %prog [options] <last-no-of-hours>

<last-no-of-hours>  Number of hours to calculate accounting data for each user.

If -e is provided, the time slice used is (END_TIME - <last-no-of-hours>, END_TIME).
Otherwise, the current time is taken as END_TIME.
'''

        self.parser.add_option('-d', '--output-dir', dest='output_dir',
            help='Directory in which to generate the accounting files. Default to local directory.',
            default='.')

        self.parser.add_option('-e', '--end-time', dest='end_time', metavar='END_TIME',
            help='End time of the requested slice. Format: %s (1970-01-01 00:00)' % TIME_FORMAT,
            default='')

        self.parser.add_option('-u', '--user-names', dest='user_names', metavar='USERNAMES',
            help='Comma separated list of user names. If given, accounting is '
            'calculated only for the users. Ignored users: %s.' % \
            ','.join(Computer.USER_IGNORE_LIST), default='')

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
            self._exit(2)
        if self.lastNoOfHours < 1:
            print "Invalid <last-no-of-hours>, cannot be less than 1"
            self._exit(2)
        self.output_dir = self.options.output_dir
        if self.options.user_names:
            self.user_names = self.options.user_names.split(',')

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
        refDate = datetime.datetime(1970, 1, 1)
        if self.options.end_time:
            now = datetime.datetime.strptime(self.options.end_time, TIME_FORMAT)
            if now > datetime.datetime.now():
                print 'ERROR: End time is in the future.', now
                self._exit(2)
        else:
            now = datetime.datetime.now()
        delta = datetime.timedelta(hours=self.lastNoOfHours)

        fromInSecs = self.total_seconds(now - delta - refDate)
        toInSecs = self.total_seconds(now - refDate)

        if self.lastNoOfHours == 24:
            daily = True
        else:
            daily = False
        Computer(fromInSecs, toInSecs, self.output_dir, daily,
                 user_names=self.user_names).compute()

    def total_seconds(self, td):
        return (td.microseconds + \
                (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 6

main = MainProgram

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
