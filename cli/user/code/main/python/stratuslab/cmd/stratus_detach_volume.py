#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Centre National de la Recherche Scientifique (CNRS)
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

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import printError
from stratuslab.commandbase.StorageCommand import StorageCommand
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Authn import AuthnFactory
from stratuslab.Exceptions import OneException

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(AuthnCommand, StorageCommand):
    """A command-line program to detach a persistent disk."""

    def __init__(self):
        super(MainProgram, self).__init__()

    def parse(self):
        self.parser.usage = '%prog [options] volume-uuid ...'
        self.parser.description = '''
Detach one or more persistent volumes (disks) that were dynamically
attached to a running virtual machine.  The volume-uuid arguments are
the unique identifiers of volumes to detach.
'''

        self.parser.add_option('-i', '--instance', dest='instance',
                               help='The ID of the instance to which the volume attaches', metavar='VM_ID',
                               default=0, type='int')

        StorageCommand.addPDiskEndpointOptions(self.parser)
        AuthnCommand.addCloudEndpointOptions(self.parser)

        super(MainProgram, self).parse()

        self.options, self.uuids = self.parser.parse_args()

    def checkOptions(self):
        super(MainProgram, self).checkOptions()
        if not self.uuids:
            printError('Please provide at least one persistent disk UUID to detach')
        if self.options.instance < 0:
            printError('Please provide a VM ID on which to detach disk')
        try:
            self._retrieveVmNode()
        except OneException, e:
            printError(e)

    def _retrieveVmNode(self):
        credentials = AuthnFactory.getCredentials(self.options)
        self.options.cloud = CloudConnectorFactory.getCloud(credentials)
        self.options.cloud.setEndpoint(self.options.endpoint)
        self.node = self.options.cloud.getVmNode(self.options.instance)

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__, self.config or {})
        configHolder.pdiskProtocol = "https"
        pdisk = VolumeManagerFactory.create(configHolder)
        for uuid in self.uuids:
            try:
                target = pdisk.hotDetach(self.options.instance, uuid)
                print 'DETACHED %s from VM %s on /dev/%s' % (uuid, self.options.instance, target)
            except Exception, e:
                printError('DISK %s: %s' % (uuid, e), exit=False)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
