#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
from optparse import OptionParser

from stratuslab import Defaults
from stratuslab.AuthnCommand import UsernamePassword
from stratuslab.CommandBase import CommandBaseSysadmin


class StorageCommand(CommandBaseSysadmin):
    @staticmethod
    def pdiskOptions():
        return PDiskEndpoint.options()

    @staticmethod
    def addPDiskEndpointOptions(parser, defaultOptions=None):
        PDiskEndpoint.addOptions(parser, defaultOptions)

    @staticmethod
    def addVolumeOptions(parser):
        PDiskVolume.addOptions(parser)

    @staticmethod
    def addOptions(parser, defaultOptions=None):
        StorageCommand.addPDiskEndpointOptions(parser, defaultOptions)
        StorageCommand.addVolumeOptions(parser)

    def checkPDiskEndpointOptionsOnly(self):
        if not self.checkPDiskEndpointOptions():
            self.parser.error('Missing persistent disk endpoint. Please provide %s'
                              % PDiskEndpoint.optionString)

    def checkPDiskEndpointOptions(self):
        return PDiskEndpoint.checkOptions(self.options)

    def checkVolumeOptions(self):
        PDiskVolume.checkOptions(self.options)

    def extractVolumeOptionsAsDict(self):
        return PDiskVolume.extractVolumeOptionsAsDict(self.options)


class PDiskEndpoint(object):
    optionString = '--pdisk-endpoint'

    @staticmethod
    def options():
        return {'pdiskEndpoint': os.getenv('STRATUSLAB_PDISK_ENDPOINT', ''),
                'pdiskProtocol': os.getenv('STRATUSLAB_PDISK_PROTOCOL', Defaults.pdiskProtocol),
                'pdiskPort': os.getenv('STRATUSLAB_PDISK_PORT', Defaults.pdiskPort),
                'pdiskUsername': os.getenv('STRATUSLAB_PDISK_USERNAME', UsernamePassword.options().get('username')),
                'pdiskPassword': os.getenv('STRATUSLAB_PDISK_PASSWORD', UsernamePassword.options().get('password'))}

    @staticmethod
    def addOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = PDiskEndpoint.options()

        # TODO: Add certificate support
        parser.add_option('--pdisk-endpoint', dest='pdiskEndpoint',
                          help='Persistent Disk service endpoint (hostname or URL). Default STRATUSLAB_PDISK_ENDPOINT',
                          default=defaultOptions['pdiskEndpoint'])
        parser.add_option('--pdisk-username', dest='pdiskUsername',
                          help='Persistent Disk service username. \
                          Default STRATUSLAB_PDISK_USERNAME, then your cloud username',
                          metavar='NAME', default=defaultOptions['pdiskUsername'])
        parser.add_option('--pdisk-password', dest='pdiskPassword',
                          help='Persistent Disk service password. \
                          Default STRATUSLAB_PDISK_PASSWORD, then your cloud password',
                          metavar='NAME', default=defaultOptions['pdiskPassword'])

    @staticmethod
    def checkOptions(options):
        if options.pdiskEndpoint:
            return True
        return False

    @staticmethod
    def checkOptionsRaiseOnError(options):
        parser = OptionParser(version="${project.version}")
        if not options.pdiskEndpoint:
            parser.error('Missing Persistent Disk service endpoint. Please provide %s'
                         % PDiskEndpoint.optionString)


class PDiskVolume(object):
    TAG_LENGTH_MAX = 40
    TAG_DEFAULT = None

    @staticmethod
    def addOptions(parser):
        parser.add_option('-t', '--tag', dest='volumeTag',
                          help='Tag of the volume.',
                          default=PDiskVolume.TAG_DEFAULT)

        parser.add_option('--private', dest='volumeVisibility',
                          help='''Set to private image''',
                          action='store_const', const="PRIVATE")

        parser.add_option('--public', dest='volumeVisibility',
                          help='''Set to public image''',
                          action='store_const', const="PUBLIC")

        parser.add_option('--machine-image-origin', dest='volumeType',
                          help='''Flag as original machine image''',
                          action='store_const', const="MACHINE_IMAGE_ORIGIN")

        parser.add_option('--machine-image-live', dest='volumeType',
                          help='''Flag as live machine image''',
                          action='store_const', const="MACHINE_IMAGE_LIVE")

        parser.add_option('--data-image-origin', dest='volumeType',
                          help='''Flag as original data image''',
                          action='store_const', const="DATA_IMAGE_ORIGIN")

        parser.add_option('--data-image-live', dest='volumeType',
                          help='''Flag as live data image''',
                          action='store_const', const="DATA_IMAGE_LIVE")

        parser.add_option('--data-image-raw-readonly', dest='volumeType',
                          help='''Flag as raw read-only data image''',
                          action='store_const', const="DATA_IMAGE_RAW_READONLY")

        parser.add_option('--data-image-raw-read-write', dest='volumeType',
                          help='''Flag as raw read-write data image''',
                          action='store_const', const="DATA_IMAGE_RAW_READ_WRITE")

    @staticmethod
    def checkOptions(options):
        PDiskVolume.checkTagLength(options)

    @staticmethod
    def checkTagLength(options):
        if not (options.volumeTag is PDiskVolume.TAG_DEFAULT):
            if len(options.volumeTag) > PDiskVolume.TAG_LENGTH_MAX:
                OptionParser(version="${project.version}"). \
                    error('Tags must have less than %d characters' %
                          PDiskVolume.TAG_LENGTH_MAX)

    @staticmethod
    def extractVolumeOptionsAsDict(options):
        keyvalues = {}

        if not (options.volumeTag is PDiskVolume.TAG_DEFAULT):
            keyvalues['tag'] = options.volumeTag

        if not (options.volumeVisibility is None):
            keyvalues['visibility'] = options.volumeVisibility

        if not (options.volumeType is None):
            keyvalues['type'] = options.volumeType

        return keyvalues
