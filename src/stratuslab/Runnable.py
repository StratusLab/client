import os
import sys

from stratuslab.CommandBase import CommandBase
from stratuslab.Runner import Runner
from stratuslab.Util import cliLineSplitChar
from stratuslab.Util import validateIp

class Runnable(CommandBase):
    '''Base class for command which need to start a machine.'''

    def __init__(self):
        self.options = None
        self.args = None
        self.image = None

        super(Runnable, self).__init__()

    def parse(self):
        options = Runner.defaultRunOptions()

        self.parser.usage = '''usage: %prog [options] image'''

        self.parser.add_option('-k', '--key', dest='userKey',
                help='SSH key to log on the machine. By default STRATUSLAB_KEY', metavar='FILE',
                default=options['userKey'])
        self.parser.add_option('-t', '--type', dest='instanceType',
                help='instance type to start', metavar='TYPE',
                default=options['instanceType'])

        self.parser.add_option('-l', '--list-type', dest='listType',
                help='list available instance type',
                default=False, action='store_true')

        self.parser.add_option('--context-file', dest='extraContextFile', metavar='FILE',
                help='extra context file with one key=value per line',
                default=options['extraContextFile'])
        self.parser.add_option('--context', dest='extraContextData', metavar='CONTEXT',
                help='extra context string (separate by %s)' % cliLineSplitChar,
                default=options['extraContextData'])

        self.parser.add_option('-u', '--username', dest='username',
                help='cloud username. Default STRATUSLAB_USERNAME',
                default=options['username'])
        self.parser.add_option('-p', '--password', dest='password',
                help='cloud password. Default STRATUSLAB_PASSWORD',
                default=options['password'])

        self.parser.add_option('--endpoint', dest='endpoint',
                help='cloud endpoint address. Default STRATUSLAB_ENDPOINT',
                default=options['endpoint'])

        self.parser.add_option('--vnc-port', dest='vncPort', metavar='PORT', type='int',
                help='VNC port number. Note for KVM it\'s the real one , not the '
                     'VNC port. So for VNC port 0 you should specify 5900, for '
                     'port 1 is 5901 and so on. ',
                default=options['vncPort'])
        self.parser.add_option('--vnc-listen', dest='vncListen', metavar='ADDRESS',
                help='IP to listen on',
                default=options['vncListen'])

        self.parser.add_option('-A', '--addressing', dest='addressing',
                help='specifies the addressing type to use for the instances (private or requested IP)',
                default=options['addressing'])
        self.parser.add_option('--nic', dest='extraNic', metavar='NAME',
                help='additional network interface',
                default=options['extraNic'])

        self.parser.add_option('--raw', dest='rawData', metavar='DATA',
                help='hypervisor raw data',
                default=options['rawData'])
        self.parser.add_option('--ramdisk', dest='vmRamdisk', metavar='PATH',
                help='machine ramdisk',
                default=options['vmRamdisk'])
        self.parser.add_option('--kernel', dest='vmKernel', metavar='PATH',
                help='machine kernel',
                default=options['vmKernel'])

        self.parser.add_option( '--template', dest='vmTemplatePath', metavar='FILE',
                help='machine template. Available substitution variables: %s' % (
                ', '.join(Runner.getVmTemplatesParameters())),
                default=options['vmTemplatePath'])

        self.options, self.args = self.parser.parse_args()

    def checkOptions(self):
        if self.options.listType:
            self.displayInstanceType()

        if len(self.args) != 1:
            self.parser.error('Please specify the machine image to start')

        self.image = self.args[0]

        if not self.options.userKey:
            self.parser.error('Unspecified user private key. See --key option.')
        if not os.path.isfile(self.options.userKey):
            self.parser.error('Key `%s` does not exist' % self.options.userKey)
        if self.options.instanceType not in Runner.getInstanceType().keys():
            self.parser.error('Specified instance type not available')
        if (self.options.addressing not in ('', 'private')) and not validateIp(self.options.addressing):
            self.parser.error('Invalide addressing')
        if self.options.extraContextFile and not os.path.isfile(self.options.extraContextFile):
            self.parser.error('Extra context file does not exist')
        if self.options.vncListen and not validateIp(self.options.vncListen):
            self.parser.error('VNC listen IP is not valid')
        if not self.options.username:
            self.parser.error('Unspecified cloud username')
        if not self.options.password:
            self.parser.error('Unspecified cloud password')
        if not self.options.endpoint:
            self.parser.error('Unspecified cloud endpoint')
        if not self.options.endpoint.startswith('http'):
            self.parser.error('Cloud endpoint must be an URL (begin with "http")')

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
