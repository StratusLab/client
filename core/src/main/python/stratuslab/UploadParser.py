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

from stratuslab.Uploader import Uploader

def buildUploadParser(parser):
    parser.usage = '''usage: %prog [options] manifest'''

    parser.add_option('-r', '--repository', dest='repoAddress',
            help='appliance repository address. Default STRATUSLAB_REPO',
            default=os.getenv('STRATUSLAB_REPO_ADDRESS'), metavar='ADDRESS')

    parser.add_option('--curl-option', dest='uploadOption', metavar='OPTION',
            help='additional curl option', default='')

    parser.add_option('-C', '--compress', dest='compressionFormat',
            help='compression format',
            default='gz', metavar='FORMAT')
    parser.add_option('-f', '--force', dest='forceUpload',
            help='force upload of the appliance even if already exist.',
            default=False, action='store_true')

    parser.add_option('--list-compression', dest='listCompressionFormat',
            help='list available compression format',
            default=False, action='store_true')

    parser.add_option('-U', '--repo-username', dest='repoUsername',
            help='repository username. Default STRATUSLAB_REPO_USERNAME',
            default=os.getenv('STRATUSLAB_REPO_USERNAME'))
    parser.add_option('-P', '--repo-password', dest='repoPassword',
            help='repository password. Default STRATUSLAB_REPO_PASSWORD',
            default=os.getenv('STRATUSLAB_REPO_PASSWORD'))

def checkUploadOptions(options, parser):
    if options.compressionFormat not in Uploader.availableCompressionFormat():
        parser.error('Unknow compression format')
    if not options.repoAddress:
        parser.error('Unspecified repository address')
    if not options.repoUsername:
        parser.error('Unspecified repository username')
    if not options.repoPassword:
        parser.error('Unspecified repository password')

