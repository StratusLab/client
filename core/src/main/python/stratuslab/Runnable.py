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

from stratuslab.Runner import Runner
from stratuslab.Util import cliLineSplitChar
from stratuslab.Util import validateIp
import Util
from AuthnCommand import AuthnCommand

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

        self.parser.add_option('-k', '--key', dest='userKey',
                help='SSH key to log on the machine. By default STRATUSLAB_KEY', metavar='FILE',
                default=defaultOptions['userKey'])
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
                help='extra context string (separate by %s)' % cliLineSplitChar,
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

        self.parser.add_option('-A', '--addressing', dest='addressing',
                help='specifies the addressing type to use for the instances (private or requested IP)',
                default=defaultOptions['addressing'])
        self.parser.add_option('--nic', dest='extraNic', metavar='NAME',
                help='additional network interface',
                default=defaultOptions['extraNic'])

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

        self._checkPrivateKey()

        if self.options.instanceType not in Runner.getInstanceType().keys():
            self.parser.error('Specified instance type not available')
        if (self.options.addressing not in ('', 'private')) and not validateIp(self.options.addressing):
            self.parser.error('Invalid addressing')
        if self.options.extraContextFile and not os.path.isfile(self.options.extraContextFile):
            self.parser.error('Extra context file does not exist')
        if self.options.vncListen and not validateIp(self.options.vncListen):
            self.parser.error('VNC listen IP is not valid')
            self.parser.error('Unspecified cloud endpoint')
        if not self.options.endpoint.startswith('http'):
            self.parser.error('Cloud endpoint must be an URL (begin with "http")')

    def _checkArgs(self):
        if len(self.args) != 1:
            self.parser.error('Please specify the machine image to start')

    def _checkPrivateKey(self):
        if self.checkCredentials:
            if not self.options.userKey:
                self.parser.error('Unspecified user private key. See --key option.')
            if not os.path.isfile(self.options.userKey):
                self.parser.error('Key `%s` does not exist' % self.options.userKey)

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
