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

from stratuslab import Defaults
from stratuslab.AuthnCommand import UsernamePassword
from stratuslab.CommandBase import CommandBaseSysadmin

class StorageCommand(CommandBaseSysadmin):
    
    @staticmethod
    def pdiskOptions():
        return PDiskEndpoint.options()

    @staticmethod
    def addPDiskEndpointOptions(parser, defaultOptions=None):
        return PDiskEndpoint.addOptions(parser, defaultOptions)

    def checkPDiskEndpointOptionsOnly(self):
        if not self.checkPDiskEndpointOptions():
            self.parser.error('Missing persistent disk endpoint. Please provide %s' 
                              % PDiskEndpoint.optionString)

    def checkPDiskEndpointOptions(self):
        return PDiskEndpoint.checkOptions(self.options)

class PDiskEndpoint(object):
    optionString = '--pdisk-endpoint'

    @staticmethod
    def options():
        return {'pdiskEndpoint' : os.getenv('STRATUSLAB_PDISK_ENDPOINT', ''),
                'pdiskProtocol' : os.getenv('STRATUSLAB_PDISK_PROTOCOL', Defaults.pdiskProtocol),
                'pdiskPort' : os.getenv('STRATUSLAB_PDISK_PORT', Defaults.pdiskPort),
                'pdiskUsername' : os.getenv('STRATUSLAB_PDISK_USERNAME', UsernamePassword.options().get('username')),
                'pdiskPassword' : os.getenv('STRATUSLAB_PDISK_PASSWORD', UsernamePassword.options().get('password'))}

    @staticmethod
    def addOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = PDiskEndpoint.options()
        
        # TODO: Add certificate support
        parser.add_option('--pdisk-endpoint', dest='pdiskEndpoint',
                          help='Persistent endpoint (hostname or URL). Default STRATUSLAB_PDISK_ENDPOINT or %s' % \
                               Defaults.marketplaceEndpoint,
                          default=defaultOptions['pdiskEndpoint'])
        parser.add_option('--pdisk-username', dest='pdiskUsername',
                          help='Persistent disk service username. \
                          Default STRATUSLAB_PDISK_USERNAME, then your cloud username', 
                          metavar='NAME', default=defaultOptions['pdiskUsername'])
        parser.add_option('--pdisk-password', dest='pdiskPassword',
                          help='Persistent disk service password. \
                          Default STRATUSLAB_PDISK_PASSWORD, then your cloud password', 
                          metavar='NAME', default=defaultOptions['pdiskPassword'])
        
    @staticmethod
    def checkOptions(options):
        if options.pdiskEndpoint:
            return True
        return False
