#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import sys

sys.path.append('/var/lib/stratuslab/python')

from stratuslab.Creator import Creator
from stratuslab.Runnable import Runnable
from stratuslab.ConfigHolder import ConfigHolder

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(Runnable):
    """A command-line program to create StratusLab image."""

    parser_usage = '''%prog [options] base-image-id'''
    parser_description = '''
Create a new image from an existing base image by adding packages and
running configuration scripts.  The base-image-id argument is the
Marketplace identifier for the initial base image.
'''

    def parse(self):

        self.parser.add_option('-n', '--name', dest='newInstalledSoftwareName',
                               help='name of the new image',
                               default='', metavar='FILE')

        self.parser.add_option('--name-version', dest='newInstalledSoftwareVersion',
                               help='version of installed software',
                               default='', metavar='VERSION')

        self.parser.add_option('--image-group', dest='newImageGroupName',
                               help='group for the new image (this corresponds to the base image folder - e.g. base, grid). '
                                    'In case of structured groups use "." as delimiter. Eg. group.subgroup.etc',
                               default='', metavar='NAME')

        self.parser.add_option('--image-version', dest='newImageGroupVersion',
                               help='version for the new image. By default a minor version of the base image is incremented.',
                               default='', metavar='VERSION')

        self.parser.add_option('--author', dest='author',
                               help='author of the new image',
                               default='', metavar='NAME')

        self.parser.add_option('--author-email', dest='authorEmail',
                               help='Email address of the author of the new image',
                               default='', metavar='EMAIL')

        self.parser.add_option('--marketplace-endpoint-newimage', dest='marketplaceEndpointNewimage',
                               help='Marketplace to register the new image manifest in. '
                                    'No default. If not provided, either base image Marketplace or defined '
                                    'by cloud site will be used.',
                               default='', metavar='URL')

        self.parser.add_option('--title', dest='title',
                               help='title of the new image',
                               default='', metavar='TEXT')

        self.parser.add_option('--comment', dest='comment',
                               help='description of the new image',
                               default='', metavar='TEXT')

        self.parser.add_option('-s', '--scripts', dest='scripts',
                               help='scripts to execute on the VM (comma separated)',
                               default='', metavar='FILE')

        self.parser.add_option('-a', '--packages', dest='packages',
                               help='packages to install on the machine (comma separated)',
                               default='', metavar='PACKAGE')

        self.parser.add_option('--os', dest='os',
                               help='operation system. By default is taken from Manifest.',
                               default='', metavar='OS')

        self.parser.add_option('--installer', dest='installer',
                               help='package installer. By default recovered based on OS.',
                               default='', metavar='NAME')

        self.parser.add_option('--extra-os-repos', dest='extraOsReposUrls',
                               help='extra repositories to install [--packages] from (comma separated). For apt '
                                    "\nbase_uri distribution [component1] ...",
                               default='', metavar='URL')

        self.parser.add_option('--exclude', dest='excludeFromCreatedImage',
                               help='exclude file/dir from new image (comma separated). Removed by default: %s' %
                                    ', '.join(Creator.excludeFromCreatedImageDefault),
                               default='', metavar='FILE')

        self.parser.add_option('--no-shutdown', dest='shutdownVm',
                               help='leave the VM running. A public IP will be assigned.',
                               default=True, action='store_false')

        self.parser.add_option('--no-upload', dest='noUpload',
                               help='do not upload the new image to an appliances repository. '
                                    "\nRequires --no-shutdown (otherwise it makes little sense ;-)",
                               default=False, action='store_true')

        self.parser.add_option('--persistent-disk', dest='persistentDiskUUID',
                               help='persistent disk UUID',
                               default=None)

        self.parser.add_option('--vm-start-timeout', dest='vmStartTimeout',
                               help='seconds to wait for VM to become available. Default: %i' %
                                    Creator.VM_START_TIMEOUT,
                               default=Creator.VM_START_TIMEOUT, type='int', metavar='TIMEOUT')

        self.parser.add_option('--vm-ping-timeout', dest='vmPingTimeout',
                               help='seconds to wait for VM\'s network to become available. Default: %i' %
                                    Creator.VM_PING_TIMEOUT,
                               default=Creator.VM_PING_TIMEOUT, type='int', metavar='TIMEOUT')

        super(MainProgram, self).parse()

    def diskSizeOptionCallback(self, option, opt_str, value, parser):
        setattr(parser.values, option.dest, 1024 * value)

    def checkOptions(self):

        super(MainProgram, self).checkOptions()

        if self.options.noUpload and self.options.shutdownVm:
            self.parser.error('If you specify --no-upload you also need to specify --no-shutdown, otherwise \
you\'ll never be able to retrieve the new image')

        if not self.options.title:
            self.parser.error('Provide a title describing the new image')

        if not self.options.comment:
            self.parser.error('Provide a comment describing the new image')

        if not self.options.author:
            self.parser.error('Provide an author for the new image')

        if not self.options.authorEmail:
            self.parser.error('Provide a valid Email address of the author of the image.')

    def doWork(self):

        configHolder = ConfigHolder(self.options.__dict__, self.config or {})
        self.creator = Creator(self.image, configHolder)

        self.creator.create()


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
