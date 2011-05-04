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
import getpass

from CommandBase import CommandBaseUser
from stratuslab import Defaults

class AuthnCommand(CommandBaseUser):
    
    @staticmethod
    def defaultRunOptions():
        options = {}
        options.update(AuthnCommand.userNamePasswordOptions())
        options.update(AuthnCommand.certPemOptions())
        options.update(AuthnCommand.certP12Options())
        return options

    @staticmethod
    def userNamePasswordOptions():
        return UsernamePassword.options()

    @staticmethod
    def certPemOptions():
        return PemCertificate.options()

    @staticmethod
    def certP12Options():
        return P12Certificate.options()

    @staticmethod
    def addUsernamePasswordOptions(parser, defaultOptions=None):
        return UsernamePassword.addOptions(parser, defaultOptions)

    @staticmethod
    def addPemCertOptions(parser, defaultOptions=None):
        return PemCertificate.addOptions(parser, defaultOptions)

    @staticmethod
    def addP12CertOptions(parser, defaultOptions=None):
        return P12Certificate.addOptions(parser, defaultOptions)

    def parse(self):
        defaultOptions = AuthnCommand.defaultRunOptions()
        
        AuthnCommand.addUsernamePasswordOptions(self.parser, defaultOptions)
        AuthnCommand.addPemCertOptions(self.parser, defaultOptions)

    def checkPemCertOptions(self):
        pemCredentials = self.options.pemCertificate and self.options.pemKey
        if not pemCredentials:
            return False
        return True

    def checkP12CertOptions(self):
        p12Credentials = self.options.p12Certificate and self.options.p12Password
        if not p12Credentials:
            return False
        return True

    def checkUsernamePasswordOptions(self):
        return UsernamePassword().checkOptions(self.options)

    def checkOptions(self):
        if not (self.checkUsernamePasswordOptions() or self.checkPemCertOptions()):
            self.parser.error('Missing credentials. Please provide either %s or %s' % 
                                (UsernamePassword.optionString, PemCertificate.optionString))

    def checkPemCertOptionsOnly(self):
        if not self.checkPemCertOptions():
            self.parser.error('Missing credentials. Please provide %s' % PemCertificate.optionString)

    def checkP12CertOptionsOnly(self):
        if not self.checkP12CertOptions():
            self.parser.error('Missing credentials. Please provide %s' % P12Certificate.optionString)

class UsernamePassword(object):
    
    optionString = '--username/--password'
    
    @staticmethod
    def options():
        return {'username': os.getenv('STRATUSLAB_USERNAME', ''),
                'password': os.getenv('STRATUSLAB_PASSWORD', '')}

    @staticmethod
    def addOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = AuthnCommand.defaultRunOptions()

        parser.add_option('-u', '--username', dest='username',
                          help='cloud username. Default STRATUSLAB_USERNAME',
                          default=defaultOptions['username'])
        parser.add_option('-p', '--password', dest='password',
                          help='cloud password. Default STRATUSLAB_PASSWORD',
                          default=defaultOptions['password'])
        return parser

    def checkOptions(self, options):
        usernamePasswordCredentials = options.username and options.password
        if not usernamePasswordCredentials:
            if options.username and not options.password:
                prompt = "'%s' at '%s' password: " % (options.username,
                                                      options.endpoint)
                options.password = getpass.getpass(prompt=prompt)
                return True
            return False

        return True

    
class PemCertificate(object):
    
    optionString = '--pem-cert/--pem-key'
    
    certDefaultLocation = Defaults.pemCertificateLocation
    keyDefaultLocation = Defaults.pemKeyLocation
    
    @staticmethod
    def options():
        return {'pemCertificate': os.getenv('STRATUSLAB_PEM_CERTIFICATE', 
                                            PemCertificate.certDefaultLocation),
                'pemKey': os.getenv('STRATUSLAB_PEM_KEY', 
                                    PemCertificate.keyDefaultLocation)}

    @staticmethod
    def addOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = AuthnCommand.defaultRunOptions()

        parser.add_option('--pem-cert', dest='pemCertificate', 
                               help='PEM certificate file. Default %s' % PemCertificate.certDefaultLocation, 
                               default=PemCertificate.certDefaultLocation, metavar='FILE')
        parser.add_option('--pem-key', dest='pemKey', 
                               help='PEM public key file. Default %s' % PemCertificate.keyDefaultLocation, 
                               default=PemCertificate.keyDefaultLocation, metavar='Key')
        return parser


class P12Certificate(object):
    
    optionString = '--p12-cert/--p12-password'

    certDefaultLocation = Defaults.p12CertificateLocation

    @staticmethod
    def options():
        return {'p12Certificate': os.getenv('STRATUSLAB_P12_CERTIFICATE', 
                                     P12Certificate.certDefaultLocation),
                'p12Password': os.getenv('STRATUSLAB_P12_PASSWORD', '')}

    @staticmethod
    def addOptions(parser, defaultOptions=None):
        if not defaultOptions:
            defaultOptions = AuthnCommand.defaultRunOptions()

        parser.add_option('--p12-cert', dest='p12Certificate', 
                          help='PKCS12 (P12) certificate file. Default %s' % P12Certificate.certDefaultLocation, 
                          default=P12Certificate.certDefaultLocation, metavar='FILE')
        parser.add_option('--p12-password', dest='p12Password', 
                          help='PKCS12 (P12) password. Default STRATUSLAB_P12_PASSWORD', 
                          default=defaultOptions['p12Password'], metavar='PASSWORD')
        return parser
