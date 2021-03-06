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

import os
import sys

sys.path.append('/var/lib/stratuslab/python')

from stratuslab.commandbase.CommandBase import CommandBase
from stratuslab.ManifestInfo import ManifestInfo, imageTypes, imageKinds, imageFormats
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Compressor import Compressor
from stratuslab.image.Image import Image
from stratuslab.vm_manager.vm_manager import VmManager
import stratuslab.Util as Util

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()


class MainProgram(CommandBase):
    """A command-line program to generate manifest."""

    def __init__(self):
        self.image = None
        super(MainProgram, self).__init__()

    def parse(self):
        self.parser.usage = '%prog [options] image'

        self.parser.description = '''
Construct a new metadata description of a machine or disk image.  The
image argument is the machine or disk image file to describe.
'''

        self.parser.add_option('--author', dest='creator',
                               help='Author of the new image',
                               default='', metavar='NAME')

        self.parser.add_option('--type', dest='type',
                               help='Image type (e.g. %s). Default: base' % ', '.join(imageTypes),
                               default='base', metavar='NAME')

        self.parser.add_option('--kind', dest='kind',
                               help='Image kind (e.g. %s). Default: machine' % ', '.join(imageKinds),
                               default='machine', metavar='NAME')

        self.parser.add_option('--os', dest='os',
                               help='Operation system',
                               default='', metavar='NAME')

        self.parser.add_option('--os-version', dest='osversion',
                               help='Operation system version',
                               default='', metavar='VERSION')

        self.parser.add_option('--os-arch', dest='arch',
                               help='Operation system architecture',
                               default='', metavar='ARCH')

        self.parser.add_option('--image-version', dest='version',
                               help='Image version',
                               default='')

        self.parser.add_option('--format', dest='format',
                               help='Image format (e.g. %s). Default: raw' % ', '.join(imageFormats),
                               default='raw')

        self.parser.add_option('--hypervisor', dest='hypervisor',
                               help='Hypervisor (e.g. kvm, xen). Default: kvm',
                               default='kvm', metavar='NAME')

        self.parser.add_option('--location', dest='locations',
                               help='Physical location of the image.',
                               default=[], metavar='URI')

        self.parser.add_option('--compression', dest='compression',
                               help='Image compression format. One of: %s' % ', '.join(Compressor.compressionFormats),
                               default='', metavar='EXT')

        self.parser.add_option('--title', dest='title',
                               help='Title to append to the manifest file',
                               default='', metavar='TEXT')

        self.parser.add_option('--tag', dest='tag',
                               help='Alternative name for the image',
                               default='', metavar='TEXT')

        self.parser.add_option('--comment', dest='comment',
                               help='Comment to append to the manifest file',
                               default='', metavar='TEXT')

        self.parser.add_option('--disks-bus', dest='disksbus',
                               help='Disks bus type. One of: %s' % ', '.join(VmManager.DISKS_BUS_AVAILABLE),
                               default=VmManager.DISKS_BUS_DEFAULT, metavar='TYPE')

        self.parser.add_option('--md5', dest='md5',
                               help='md5 checksum',
                               default='', metavar='HEX')
        self.parser.add_option('--sha1', dest='sha1',
                               help='sha1 checksum',
                               default='', metavar='HEX')
        self.parser.add_option('--sha256', dest='sha256',
                               help='sha256 checksum',
                               default='', metavar='HEX')
        self.parser.add_option('--sha512', dest='sha512',
                               help='sha512 checksum',
                               default='', metavar='HEX')

        self.parser.add_option('--no-md5', dest='noMd5',
                               help='do not calculate md5 checksum',
                               default=False, action='store_true')
        self.parser.add_option('--no-sha256', dest='noSha256',
                               help='do not calculate sha256 checksum',
                               default=False, action='store_true')
        self.parser.add_option('--no-sha512', dest='noSha512',
                               help='do not calculate sha512 checksum',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

    def checkOptions(self):
        if len(self.args) != 1:
            self.parser.error('Please specify an image')
        self.image = self.args[0]

        if not os.path.isfile(self.image):
            self.parser.error('Image does not exist: ' + self.image)

        if not self.options.locations:
            self.options.__dict__.update({'locations': []})
            Util.printWarning("Image physical location (URL) was not provided. "
                              "You'll have to set it manually in the resulting manifest.")
        else:
            self.options.__dict__.update({'locations': [self.options.__dict__['locations']]})

        if not self.options.compression:
            # Guess compression from file name if not given explicitly.
            compression = Compressor.getCompressionFormat(self.image)
            self.options.__dict__.update({'compression': compression})

        if self.options.disksbus not in VmManager.DISKS_BUS_AVAILABLE:
            self.parser.error("Unknown disks bus type %s. Available types: %s" %
                              (self.options.disksbus, ', '.join(VmManager.DISKS_BUS_AVAILABLE)))

    def doWork(self):
        self._calculateCheckSums()

        configHolder = ConfigHolder(self.options.__dict__)
        manifest = ManifestInfo(configHolder)
        manifest.buildAndSave()

    def _calculateCheckSums(self):
        checkSumNames = ManifestInfo.CHECKSUM_NAMES
        # checksums to do if we were not given any
        checkSums = dict([(x, getattr(self.options, x, '')) for x in checkSumNames])
        checkSumsToDo = [k for k, v in checkSums.items() if not v]
        # remove the ones we told not to do
        for c in checkSumsToDo[:]:
            if getattr(self.options, 'no%s' % c.title(), False):
                checkSumsToDo.remove(c)
        if not checkSumsToDo and not self.options.sha1:
            checkSumsToDo = ManifestInfo.MANDATORY_CHECKSUMS

        bytes, chksums = Image.checksumImage(self.image, checkSumsToDo)

        self.options.__dict__.update({'bytes': bytes})
        self.options.__dict__.update(chksums)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
