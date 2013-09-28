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

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.AuthnCommand import AuthnCommand
from stratuslab.vm_manager.vm_manager_factory import VmManagerFactory


class InstanceCommand(AuthnCommand):
    """A command-line program to kill a virtual machine."""

    def __init__(self):
        self.vmIds = []
        super(InstanceCommand, self).__init__()

    def parse(self):
        self.parser.usage = self.parser_usage
        self.parser.description = self.parser_description

        self.parser.add_option('-i', '--input', dest='inVmIdsFile',
                               help='file containing line separated vm-ids', metavar='FILE',
                               default=None)

        AuthnCommand.addCloudEndpointOptions(self.parser)

        super(InstanceCommand, self).parse()

        self.options, self.vmIds = self.parser.parse_args()

    def checkOptions(self):
        AuthnCommand.checkCloudEndpointOptionsOnly(self)

        if not self.vmIds and not self.options.inVmIdsFile:
            self.parser.error('Missing vm-id or input file (-i/--input)')

        super(InstanceCommand, self).checkOptions()

    def _get_runner(self):
        configHolder = ConfigHolder(self.options.__dict__)
        return VmManagerFactory.create(None, configHolder)

    def shutdownInstances(self):
        self._get_runner().shutdownInstances(self.vmIds)

    def killInstances(self):
        self._get_runner().killInstances(self.vmIds)

