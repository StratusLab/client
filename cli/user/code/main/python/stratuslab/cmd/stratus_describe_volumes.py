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

from stratuslab.commandbase.StorageCommand import StorageCommand
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.ConfigHolder import ConfigHolder

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(AuthnCommand, StorageCommand):
    """A command-line program to view the persistent disk."""

    def __init__(self):
        super(MainProgram, self).__init__()

    def parse(self):
        self.parser.usage = '%prog [options] [volume-uuid ...]'

        self.parser.description = '''
Provides information about the volumes (disks) associated with the
given identifiers.  Provides information about all volumes if no
identifiers are given.  The volume-uuid arguments are the volume
identifiers.
'''

        self.parser.add_option('-f', '--filter', dest='filters',
                               help='''Filter available disk with specified properties.
Name are the one specified when describing disk properties. Values can be python
regex pattern.
Example: --filter owner:john --filter tag:grid-* will show only john's disk
that have a tag matching the regex pattern.''',
                               metavar='name:value', action='append', default=[])

        StorageCommand.addPDiskEndpointOptions(self.parser)

        super(MainProgram, self).parse()

        self.options, self.uuids = self.parser.parse_args()

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__, self.config or {})
        pdisk = VolumeManagerFactory.create(configHolder)
        filters = self._formatFilter()
        volumes = pdisk.describeVolumes(filters)
        self._printVolumes(volumes)

    def _printVolumes(self, volumes):
        if not len(volumes):
            print 'No disk to show'
        for disk in volumes:
            print ':: DISK %s' % disk['uuid']
            self._printDict(disk, ['uuid', ])

    def _printDict(self, dictionary, excludeKey=[]):
        for k, v in dictionary.items():
            if k not in excludeKey:
                print '\t%s: %s' % (k, v)

    def _formatFilter(self):
        # produce {key:[value,]}
        filters = {}
        self._addUuidToFilters()
        for filt in self.options.filters:
            key = filt.split(':')[0]
            value = ':'.join(filt.split(':')[1:]).lstrip().rstrip()
            if key in filters:
                if value not in filters[key]:
                    filters[key].append(value)
            else:
                filters[key] = [value, ]
        return filters

    def _addUuidToFilters(self):
        for uuid in self.uuids:
            self.options.filters.append('uuid:%s' % uuid)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
