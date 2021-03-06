#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys

from stratuslab.commandbase.AuthnCommand import AuthnCommand


sys.path.append('/var/lib/stratuslab/python')

from stratuslab.Monitor import Monitor, MultisiteMonitor
from stratuslab.ConfigHolder import ConfigHolder
import stratuslab.Util as Util

from stratuslab.pat.Command import PortTranslationCommand

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(AuthnCommand, PortTranslationCommand):
    """A command-line program to monitor the state of virtual machines."""

    def __init__(self):
        self.vmIds = []
        self.config = {}
        super(MainProgram, self).__init__()

    def parse(self):

        self.parser.usage = '%prog [options] [vm-id ...]'

        self.parser.description = '''
Provides information about the virtual machine with the given
identifiers or all virtual machine if no identifier is given.  The
vm-id arguments are the identifiers of the machines to list. All
virtual machines will be listed if no argument is given.
'''

        PortTranslationCommand.addCommonOptions(self.parser)
        AuthnCommand.addCloudEndpointOptions(self.parser)
        Monitor.addOptions(self.parser)

        self.parser.add_option('-m', dest='multi_site', action='store_true',
                               help='Print state of virtual machines on multiple sites. '
                                    '"endpoints" parameter should be set in user configuration '
                                    'file.',
                               default=False)

        super(MainProgram, self).parse()

        self.options, self.vmIds = self.parser.parse_args()

    def checkOptions(self):
        AuthnCommand.checkCloudEndpointOptionsOnly(self)
        PortTranslationCommand.checkCommonOptions(self)
        super(MainProgram, self).checkOptions()

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__, self.config or {})

        if not self.vmIds and (self.options.multi_site and self.config.get('endpoints')):
            result = MultisiteMonitor(configHolder).formatVmList()
        else:
            monitor = Monitor(configHolder)
            if self.vmIds:
                vm_info_list = monitor.vmDetail(self.vmIds)
                if len(vm_info_list) == 1 and self.verboseLevel > Util.VERBOSE_LEVEL_DETAILED:
                    result = monitor.formatVmAllAttributes(vm_info_list)
                else:
                    result = monitor.formatVmDetails(vm_info_list)
            else:
                vm_info_list = monitor.listVms()
                result = monitor.formatVmList(vm_info_list)

        sys.stdout.write(result)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
