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

import os
import sys

sys.path.append('/var/lib/stratuslab/python')

import stratuslab.Util as Util
from stratuslab.commandbase.CommandBase import CommandBaseUser
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.commandbase.AuthnCommand import P12Certificate
from stratuslab.Signator import Signator

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(CommandBaseUser):
    """A command-line program to sign image metadata."""

    def __init__(self):
        self.manifestFile = None
        self.args = None
        super(MainProgram, self).__init__()

    def parse(self):

        self.parser.usage = '''%prog [options] metadata-file'''

        self.parser.description = '''
Sign the given metadata description of a machine or disk image.  The
metadata-file argument is the file containing the metadata to sign.
'''

        P12Certificate.addOptions(self.parser)

        self.parser.add_option('--output', dest='outputManifestFile',
                               help='signed metadata file (same as input; input moved to *.orig)',
                               default=None)

        self.parser.add_option('--email', dest='email',
                               help='email address if not in certificate',
                               default='')

        self.options, self.args = self.parser.parse_args()

    def checkOptions(self):
        if not self.args:
            self.parser.error('Missing metadata file')

        self.manifestFile = self.args[0]

        isFile = os.path.isfile(self.manifestFile)
        exists = os.path.exists(self.manifestFile)
        if not (exists and isFile):
            self.parser.error('Metadata file doesn\'t exist or is not a file')

        if not P12Certificate.checkOptions(self.options):
            self.parser.error('Missing credentials. Please provide %s' % P12Certificate.optionString)

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__)
        signator = Signator(self.manifestFile, configHolder)
        isError = signator.sign()
        if isError:
            Util.printError('Error signing metadata file')
        else:
            Util.printDetail('Metadata file successfully signed: %s' % signator.outputManifestFile)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
