#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010-11, GRNET, SixSq Sarl.
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

sys.path.append('/var/lib/stratuslab/python')

from stratuslab.vm_manager.vm_manager_factory import VmManagerFactory
from stratuslab.vm_manager.vm_manager import VmManager
from stratuslab.Runnable import Runnable
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Cluster import Cluster
from stratuslab.commandbase.StorageCommand import StorageCommand

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(Runnable):
    """A command-line program to run a virtual machine."""

    parser_description = '''
Runs a batch cluster using the given image.  The image argument is the
Marketplace ID of image with batch software installed.
'''

    def parse(self):
        options = VmManager.defaultRunOptions()

        self.parser.add_option('--shared-folder', dest='shared_folder', action='store',
                               help='folder to share over NFS',
                               default=None, type='string')

        self.parser.add_option('--ssh-hostbased', dest='ssh_hostbased', action='store_true',
                               help='Enable cluster integration through hostbased ssh authentication',
                               default=False)

        self.parser.add_option('--cluster-admin', dest='cluster_admin', action='store',
                               help='Username for cluster administrator (default root)',
                               default='root', type='string')

        self.parser.add_option('--cluster-user', dest='cluster_user', action='store',
                               help='Additional username to be created',
                               default=None, type='string')

        self.parser.add_option('--mpi-machine-file', dest='mpi_machine_file', action='store_true',
                               help='Defines that a machinefile should be prepared for MPI, listing all available '
                                    'workers and their respective number of cores (slot value). (Default=False)',
                               default=False)

        self.parser.add_option('--include-master', dest='include_master', action='store_true',
                               help='Defines that the master node should be considered '
                                    'as part of the worker nodes. (Default=False)',
                               default=False)

        self.parser.add_option('--add-packages', dest='add_packages', action='store',
                               help='Provide comma separated list of additional packages that you wish to install',
                               default=None, type='string')

        self.parser.add_option('--master-vmid', dest='master_vmid', action='store',
                               help='VMID of master node if this has been instantiated separately',
                               default=None, type='int')

        self.parser.add_option('--tolerate-failures', dest='tolerate_failures', action='store_true',
                               help='If set true the program will try to configure the '
                                    'cluster with as many nodes as it can  '
                                    'in case some of them fail during instantiation',
                               default=False)

        self.parser.add_option('--clean-after-failure', dest='clean_after_failure', action='store_true',
                               help='In case the program stops on failure it will try to kill all VMs instantiated',
                               default=True)

        self.parser.add_option('-n', '--number', dest='instanceNumber',
                               help='number of machines to start (default 1) for the cluster', metavar='INT',
                               default=options['instanceNumber'], type='int')

        self.parser.add_option('--save', dest='saveDisk', action='store_true',
                               help='save image after VM shutdown',
                               default=False)

        self.parser.add_option('-o', '--output', dest='outVmIdsFile',
                               help='save vm-id to a file', metavar='FILE',
                               default=None)

        self.parser.add_option('--volatile-disk', dest='extraDiskSize',
                               help='volatile data disk size in GB', metavar='INT',
                               action='callback', callback=self.diskSizeOptionCallback,
                               default=0, type='int')

        self.parser.add_option('--persistent-disk', dest='persistentDiskUUID',
                               help='persistent disk UUID',
                               default=None)

        self.parser.add_option('--readonly-disk', dest='readonlyDiskId',
                               help='marketplace readonly disk image ID',
                               default=None, metavar='MARKETPLACEID')

        self.parser.add_option('--qcow-disk-format', dest='useQcowDiskFormat',
                               help='launch instance from an image in qcow2 disk format. This option requires ',
                               action='store_true',
                               default=False)

        self.parser.add_option('--address', dest='specificAddressRequest',
                               help='request a specific ip address',
                               metavar='IP', default=None)

        self.parser.add_option('--no-check-image-url', dest='noCheckImageUrl',
                               help='Do not check image availability.',
                               action='store_true',
                               default=False)

        self.parser.add_option('--vm-name', dest='vmName',
                               help='name of VM. If not given, a default name will be assigned by cloud layer.',
                               metavar='NAME', default=options['vmName'])

        StorageCommand.addPDiskEndpointOptions(self.parser)

        super(MainProgram, self).parse()

    def diskSizeOptionCallback(self, option, opt_str, value, parser):
        setattr(parser.values, option.dest, 1024 * value)

    def doWork(self):
        configHolder = ConfigHolder(self.options.__dict__)
        runner = VmManagerFactory.create(self.image, configHolder)
        cluster = Cluster(configHolder, runner, self.options.master_vmid)

        printAction('Starting cluster')
        runner.runInstance()

        cluster.deploy()

        printStep('Done!')


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
        return 0
