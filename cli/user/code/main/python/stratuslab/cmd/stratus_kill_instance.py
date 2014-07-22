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

sys.path.append('/var/lib/stratuslab/python')

from stratuslab.commandbase.InstanceCommand import InstanceCommand

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(InstanceCommand):
    """A command-line program to kill a virtual machine."""

    def parse(self):
        self.parser_usage = '''%prog [options] vm-id ...'''
        self.parser_description = '''
Stop one or more virtual machines and release their associated
resources.  The vm-id arguments are the identifiers of the VM
instances to stop.
'''
        super(MainProgram, self).parse()

    def doWork(self):
        self.killInstances()


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
