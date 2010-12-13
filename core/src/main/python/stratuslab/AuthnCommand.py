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
        options = {}
        options.update(AuthnCommand.userNamePasswordOptions())
        options.update(AuthnCommand.certPemOptions())
        options.update(AuthnCommand.certP12Options())
        return options

    @staticmethod
    def userNamePasswordOptions():
        return {'username': os.getenv('STRATUSLAB_USERNAME', ''),
                'password': os.getenv('STRATUSLAB_PASSWORD', '')}

    @staticmethod
    def certPemOptions():
        return {'pemCert': os.getenv('STRATUSLAB_PEM_CERTIFICATE', ''),
                'pemKey': os.getenv('STRATUSLAB_PEM_KEY', '')}

    @staticmethod
    def certP12Options():
        return {'p12Cert': os.getenv('STRATUSLAB_P12_CERTIFICATE', ''),
                'p12Password': os.getenv('STRATUSLAB_P12_PASSWORD', '')}

    @staticmethod
    def addPemCertOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = AuthnCommand.defaultRunOptions()

        parser.add_option('--pem-cert', dest='pemCert', 
                               help='PEM certificate file. Default STRATUSLAB_PEM_CERTIFICATE', 
                               default=defaultOptions['pemCert'], metavar='FILE')
        parser.add_option('--pem-key', dest='pemKey', 
                               help='PEM certificate password. Default STRATUSLAB_PEM_KEY', 
                               default=defaultOptions['pemKey'], metavar='KEY')
        return parser

    @staticmethod
    def addP12CertOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = AuthnCommand.defaultRunOptions()

        parser.add_option('--p12-cert', dest='p12Cert', 
                          help='PKCS12 (P12) certificate file. Default STRATUSLAB_P12_CERTIFICATE', 
                          default=defaultOptions['p12Cert'], metavar='FILE')
        parser.add_option('--p12-password', dest='p12Password', 
                          help='PKCS12 (P12) password. Default STRATUSLAB_P12_PASSWORD', 
                          default=defaultOptions['p12Password'], metavar='PASSWORD')
        return parser

    certPemOptionString = '--pem-cert/--pem-key'
    certP12OptionString = '--p12-cert/--p12-password'

    def parse(self):
        defaultOptions = AuthnCommand.defaultRunOptions()

        self.parser.add_option('-u', '--username', dest='username',
                help='cloud username. Default STRATUSLAB_USERNAME',
                default=defaultOptions['username'])
        self.parser.add_option('-p', '--password', dest='password',
                help='cloud password. Default STRATUSLAB_PASSWORD',
                default=defaultOptions['password'])

        AuthnCommand.addPemCertOptions(self.parser, defaultOptions)

        AuthnCommand.addP12CertOptions(self.parser, defaultOptions)


    def checkPemCertOptions(self):
        pemCredentials = self.options.pemCert and self.options.pemKey
        if not pemCredentials:
            return False
        return True

    def checkP12CertOptions(self):
        p12Credentials = self.options.p12Cert and self.options.p12Password
        if not p12Credentials:
            return False
        return True

    def checkUsernamePasswordOptions(self):
        usernamePasswordCredentials = self.options.username and self.options.password
        if not usernamePasswordCredentials:
            return False
        return True

    def checkOptions(self):
        if not (self.checkUsernamePasswordOptions() or self.checkPemCertOptions()):
            self.parser.error('Missing credentials. Please provide either --username/--password or %s' % AuthnCommand.certPemOptionString)

    def checkPemCertOptionsOnly(self):
        if not self.checkPemCertOptions():
            self.parser.error('Missing credentials. Please provide %s' % AuthnCommand.certPemOptionString)

    def checkP12CertOptionsOnly(self):
        if not self.checkP12CertOptions():
            self.parser.error('Missing credentials. Please provide %s' % AuthnCommand.certP12OptionString)

