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

from stratuslab.commandbase.AuthnCommand import AuthnCommand


sys.path.append('/var/lib/stratuslab/python')

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.marketplace.Uploader import Uploader
from stratuslab.Exceptions import InputException

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(AuthnCommand):
    """A command-line program to upload StratusLab appliance."""

    def __init__(self):
        self.manifest = None
        super(MainProgram, self).__init__()

    def parse(self):
        Uploader.buildUploadParser(self.parser)

        self.parser.usage = '''%prog [options] metadata-file'''

        self.parser.description = '''
Uploads metadata about a machine or disk image to the Marketplace.
The metadata-file argument is the signed metadata file to upload.
'''

        self.options, self.args = self.parser.parse_args()

    def checkOptions(self):
        if len(self.args) != 1:
            self.parser.error('Please specify an image manifest')
        self.manifest = self.args[0]

        Uploader.checkUploadOptions(self.options, self.parser)

        if not os.path.isfile(self.manifest):
            self.parser.error('Image manifest does not exist: ' + self.manifest)

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__)
        uploader = Uploader(configHolder)

        try:
            url = uploader.upload(self.manifest)
            print url
        except InputException, e:
            print e
            sys.exit(1)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
