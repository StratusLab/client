#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552.
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique
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

from stratuslab import Defaults
from stratuslab import Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Monitor import Monitor
from stratuslab.pat.Command import PortTranslationCommand

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(AuthnCommand, PortTranslationCommand):
    """A command-line program to connect to virtual machines."""

    def __init__(self):
        self.vmIds = []
        super(MainProgram, self).__init__()

    def parse(self):
        defaultOptions = self._setDefaultOptions()

        self.parser.usage = '%prog [options] vm-id'
        self.parser.description = '''
Connects to the given virtual machine via SSH.  Automatically retries
the connection on failures. The vm-id argument is the virtual machine
identifier.
'''

        self.parser.add_option('-k', '--key', dest='userPrivateKeyFile',
                               help='SSH private key file to log on the machine. Default %s.' % defaultOptions[
                                   'userPrivateKeyFile'],
                               metavar='FILE',
                               default=defaultOptions['userPrivateKeyFile'])

        PortTranslationCommand.addCommonOptions(self.parser)
        AuthnCommand.addCloudEndpointOptions(self.parser)

        super(MainProgram, self).parse()

        self.options, self.vmIds = self.parser.parse_args()

    def _setDefaultOptions(self):
        sshPublicKey = os.getenv('STRATUSLAB_KEY', Defaults.sshPublicKeyLocation)
        sshPrivateKey = sshPublicKey.strip('.pub')
        defaultOptions = {
            'userPublicKeyFile': sshPublicKey,
            'userPrivateKeyFile': sshPrivateKey
        }

        return defaultOptions

    def checkOptions(self):
        if not self.vmIds:
            self.parser.error('Missing vm-id')

        AuthnCommand.checkCloudEndpointOptionsOnly(self)
        PortTranslationCommand.checkCommonOptions(self)
        self._checkPrivateKeyFile()

        super(MainProgram, self).checkOptions()

    def _checkPrivateKeyFile(self):
        if not self.options.userPrivateKeyFile:
            self.parser.error('Unspecified user private key. See --key option.')

        if not os.path.isfile(self.options.userPrivateKeyFile):
            self.parser.error('Private key `%s` does not exist' % self.options.userPrivateKeyFile)

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__)
        monitor = Monitor(configHolder)
        for vmId in self.vmIds:
            host, port = monitor.getVmConnectionInfo(vmId)
            if host and port:
                Util.sshInteractive(host, port=port, sshKey=self.options.userPrivateKeyFile)
            else:
                sys.stderr.write("Couldn't find enough information to connect to VM '%s'\n" % vmId)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
