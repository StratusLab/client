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
import sys

from stratuslab.Runner import Runner
from stratuslab.Uploader import Uploader
from stratuslab.marketplace.Downloader import Downloader
from stratuslab.AuthnCommand import AuthnCommand
import stratuslab.Util as Util

class Runnable(AuthnCommand):
    '''Base class for command which need to start a machine.'''

    def __init__(self):
        self.options = None
        self.args = None
        self.image = None
        self.checkCredentials = True

        super(Runnable, self).__init__()

    def parse(self):
        defaultOptions = Runner.defaultRunOptions()

        self.parser.usage = '''%prog [defaultOptions] image'''

        self.parser.add_option('-k', '--key', dest='userPublicKeyFile',
                help='SSH public key(s) (.pub) to log on the machine. Default order %s, STRATUSLAB_KEY. In case of multiple keys, concatenate them to the file.' % defaultOptions['userPublicKeyFile'], 
                metavar='FILE',
                default=defaultOptions['userPublicKeyFile'])

        self.parser.add_option('-t', '--type', dest='instanceType',
                help='instance type to start', metavar='TYPE',
                default=defaultOptions['instanceType'])

        self.parser.add_option('-l', '--list-type', dest='listType',
                help='list available instance type',
                default=False, action='store_true')

        self.parser.add_option('--context-file', dest='extraContextFile', metavar='FILE',
                help='extra context file with one key=value per line',
                default=defaultOptions['extraContextFile'])
        self.parser.add_option('--context', dest='extraContextData', metavar='CONTEXT',
                help='extra context string (separate by %s)' % Util.cliLineSplitChar,
                default=defaultOptions['extraContextData'])

        self.parser.add_option('--endpoint', dest='endpoint',
                help='cloud endpoint address. Default STRATUSLAB_ENDPOINT',
                default=defaultOptions['endpoint'])

        self.parser.add_option('--vnc-port', dest='vncPort', metavar='PORT', type='int',
                help='VNC port number. Note for KVM it\'s the real one , not the '
                     'VNC port. So for VNC port 0 you should specify 5900, for '
                     'port 1 is 5901 and so on. ',
                default=defaultOptions['vncPort'])
        self.parser.add_option('--vnc-listen', dest='vncListen', metavar='ADDRESS',
                help='IP to listen on',
                default=defaultOptions['vncListen'])

        self.parser.add_option('--raw', dest='rawData', metavar='DATA',
                help='hypervisor raw data',
                default=defaultOptions['rawData'])
        self.parser.add_option('--ramdisk', dest='vmRamdisk', metavar='PATH',
                help='machine ramdisk',
                default=defaultOptions['vmRamdisk'])
        self.parser.add_option('--kernel', dest='vmKernel', metavar='PATH',
                help='machine kernel',
                default=defaultOptions['vmKernel'])

        self.parser.add_option( '--template', dest='vmTemplatePath', metavar='FILE',
                help='machine template. Available substitution variables: %s' % (
                ', '.join(Runner.getVmTemplatesParameters())),
                default=defaultOptions['vmTemplatePath'])

        self.parser.add_option('--marketplace-endpoint', dest='marketPlaceEndpoint',
                help='Market place endpoint. Default %s or %s' % (Uploader.MARKETPLACE_ADDRESS, Downloader.ENDPOINT),
                default=None)

        super(Runnable, self).parse()

        options, self.args = self.parser.parse_args()
        self._assignOptions(defaultOptions, options)


    def _assignOptions(self, defaultOptions, options):
        obj = lambda: None
        Util.assignAttributes(obj, defaultOptions)
        Util.assignAttributes(obj, options.__dict__)
        self.options = obj


    def checkOptions(self):
        if self.options.listType:
            self.displayInstanceType()

        self._checkArgs()

        self.image = self.args[0]

        self._checkKeyPair()

        if self.options.instanceType not in Runner.getInstanceType().keys():
            self.parser.error('Specified instance type not available')
        if self.options.extraContextFile and not os.path.isfile(self.options.extraContextFile):
            self.parser.error('Extra context file does not exist')
        if self.options.vncListen and not Util.validateIp(self.options.vncListen):
            self.parser.error('VNC listen IP is not valid')
            self.parser.error('Unspecified cloud endpoint')

        if not self.options.marketPlaceEndpoint:
            self.options.marketPlaceEndpoint = os.getenv(Uploader.MARKETPLACE_ADDRESS, Downloader.ENDPOINT) 

        super(Runnable, self).checkOptions()

    def _checkArgs(self):
        if len(self.args) != 1:
            self.parser.error('Please specify the machine image to start')

    def _checkKeyPair(self):
        if self.checkCredentials:
            if not self.options.userPublicKeyFile:
                self.parser.error('Unspecified user public key. See --key option.')

            self.options.userPrivateKeyFile = self.options.userPublicKeyFile.strip('.pub')

            for key in [self.options.userPublicKeyFile, self.options.userPrivateKeyFile]:
                if not os.path.isfile(key):
                    self.parser.error('Key `%s` does not exist' % key)

    def displayInstanceType(self):
        types = Runner.getInstanceType()
        columnSize = 10

        print 'Type'.ljust(columnSize),
        print 'CPU'.ljust(columnSize),
        print 'RAM'.ljust(columnSize),
        print 'SWAP'.ljust(columnSize)
        for name, spec in types.items():
            cpu, ram, swap = spec
            print '%s %s %s %s' % (name.ljust(columnSize),
                            ('%s CPU' % cpu).ljust(columnSize),
                            ('%s MB' % ram).ljust(columnSize),
                            ('%s MB' % swap).ljust(columnSize))
        sys.exit(0)
