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

from CommandBase import CommandBase

class AuthnCommand(CommandBase):
    
    @staticmethod
    def defaultRunOptions():
        return {'username': os.getenv('STRATUSLAB_USERNAME', ''),
                'password': os.getenv('STRATUSLAB_PASSWORD', ''),
                'pemCert': os.getenv('STRATUSLAB_PEM_CERTIFICATE', ''),
                'pemKey': os.getenv('STRATUSLAB_PEM_PASSWORD', '')}

    def parse(self):
        defaultOptions = AuthnCommand.defaultRunOptions()

        self.parser.add_option('-u', '--username', dest='username',
                help='cloud username. Default STRATUSLAB_USERNAME',
                default=defaultOptions['username'])
        self.parser.add_option('-p', '--password', dest='password',
                help='cloud password. Default STRATUSLAB_PASSWORD',
                default=defaultOptions['password'])

        self.parser.add_option('--pem-cert', dest='pemCert',
                help='PEM certificate file. Default STRATUSLAB_PEM_CERTIFICATE',
                default=defaultOptions['pemCert'], metavar='FILE')
        self.parser.add_option('--pem-key', dest='pemKey',
                help='PEM certificate password. Default STRATUSLAB_PEM_PASSWORD',
                default=defaultOptions['pemKey'], metavar='PASSWORD')


    def checkOptions(self):
        usernamePasswordCredentials = self.options.username and self.options.password
        pemCredentials = self.options.pemCert and self.options.pemKey
        if not (usernamePasswordCredentials or pemCredentials):
            self.parser.error('Missing credentials. Please provide either --username/--password or --pem-cert/--pem-key')

