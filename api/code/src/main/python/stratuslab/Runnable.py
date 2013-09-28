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

from stratuslab.AuthnCommand import AuthnCommand
import stratuslab.Util as Util

from marketplace.Util import Util as MarketplaceUtil
from stratuslab.vm_manager.vm_manager import VmManager


class Runnable(AuthnCommand):
    """Base class for command which need to start a machine."""
    parser_usage = '''%prog [options] image'''
    parser_description = 'image - Marketplace image ID or PDISK volume UUID'

    def __init__(self):
        self.options = None
        self.args = None
        self.image = None

        super(Runnable, self).__init__()

    def parse(self):
        default_options = VmManager.defaultRunOptions()

        self.parser.usage = self.parser_usage

        self.parser.description = self.parser_description

        self.parser.add_option('-k', '--key', dest='userPublicKeyFile',
                               help='SSH public key(s) (.pub) to log on the machine. Default %s. In case of multiple keys, concatenate them to the file.' %
                                    default_options['userPublicKeyFile'],
                               metavar='FILE',
                               default=default_options['userPublicKeyFile'])

        self.parser.add_option('-t', '--type', dest='instanceType',
                               help='instance type to start (see --list-types for default)', metavar='TYPE',
                               default=VmManager.DEFAULT_INSTANCE_TYPE)

        self.parser.add_option('--list-type', dest='listType',
                               help='list available instance types (deprecated)',
                               action='store_true')

        self.parser.add_option('-l', '--list-types', dest='listType',
                               help='list available instance types',
                               default=False, action='store_true')

        self.parser.add_option('--cpu', dest='vmCpu',
                               help='number of CPU cores',
                               default=None)

        self.parser.add_option('--ram', dest='vmRam',
                               help='RAM in megabytes',
                               default=None)

        self.parser.add_option('--swap', dest='vmSwap',
                               help='swap space in megabytes',
                               default=None)

        self.parser.add_option('--context-file', dest='extraContextFile', metavar='FILE',
                               help='extra context file with one key=value per line',
                               default=default_options['extraContextFile'])
        self.parser.add_option('--context', dest='extraContextData', metavar='CONTEXT',
                               help='extra context string (separate by %s)' % Util.cliLineSplitChar,
                               default=default_options['extraContextData'])

        self.parser.add_option('--cloud-init', dest='cloudInit', metavar='PAIRS',
                               help='mimetype,file pairs (separate by %s)' % Util.cliLineSplitChar,
                               default=default_options['cloudInit'])

        self.parser.add_option('--vnc-port', dest='vncPort', metavar='PORT', type='int',
                               help='VNC port number. Note for KVM it\'s the real one, not the '
                                    'VNC port. So for VNC port 0 you should specify 5900, for '
                                    'port 1 is 5901 and so on. ',
                               default=default_options['vncPort'])
        self.parser.add_option('--vnc-listen', dest='vncListen', metavar='ADDRESS',
                               help='IP to listen on',
                               default=default_options['vncListen'])

        self.parser.add_option('--vm-requirements', dest='vmRequirements', metavar='REQUIREMENTS',
                               help='Advanced requirements for VM placement. '
                                    'Available values depend on the cloud configuration. '
                                    'e.g. --vm-requirements \'CLUSTER = \\"test\\" & MAGICNUMBER = 42\'',
                               default=None)

        self.parser.add_option('--vm-template-file', dest='vmTemplateFile', metavar='FILE',
                               help='VM template file. Default %s' % default_options['vmTemplateFile'],
                               default=default_options['vmTemplateFile'])

        self.parser.add_option('--vm-cpu-amount', dest='vmCpuAmount', metavar='CPU', type='float',
                               help='Percentage of CPU divided by 100 required for the Virtual Machine. '
                                    'Half a processor is written 0.5. No default. If not provided, CPU value from '
                                    'predefined instance types is used.',
                               default=default_options['vmCpuAmount'])

        self.parser.add_option('--vm-disks-bus', dest='vmDisksBus', metavar='BUSTYPE',
                               help='VM disks bus type defined for all disks. Overrides "disks-bus" '
                                    'element value defined in image manifest. '
                                    'Available types: %s. ' % ', '.join(VmManager.DISKS_BUS_AVAILABLE) +
                                    'If not provided, by default the value is taken from disks-bus '
                                    'element of image manifest. If the latter is not set, '
                                    'by default "%s" is assumed.' % VmManager.DISKS_BUS_DEFAULT,
                               default=default_options['vmDisksBus'])

        MarketplaceUtil.addEndpointOption(self.parser)

        AuthnCommand.addCloudEndpointOptions(self.parser)

        super(Runnable, self).parse()

        options, self.args = self.parser.parse_args()

        self._assignOptions(default_options, options)

    def _assignOptions(self, default_options, options):
        obj = lambda: None
        Util.assignAttributes(obj, default_options)
        Util.assignAttributes(obj, options.__dict__)
        self.options = obj

    def checkOptions(self):

        if self.options.listType:
            return

        self._check_args()

        self.image = self.args[0]

        AuthnCommand.checkCloudEndpointOptionsOnly(self)

        if self.options.extraContextFile and not os.path.isfile(self.options.extraContextFile):
            self.parser.error('Extra context file does not exist')
        if self.options.vncListen and not Util.validateIp(self.options.vncListen):
            self.parser.error('VNC listen IP is not valid')

        MarketplaceUtil.checkEndpointOption(self.options)

        super(Runnable, self).checkOptions()

    def _check_args(self):
        if len(self.args) != 1:
            self.parser.error('Please specify the machine image to start')
