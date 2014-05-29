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
import xmlrpclib

import urllib
from stratuslab.Exceptions import ValidationException
from stratuslab.Configurator import SimpleConfigParser
from stratuslab import Defaults

class AuthnFactory(object):
    
    @staticmethod
    def getCredentials(runnable):

        if AuthnFactory._useLocalHostCredentials(runnable):
            return LocalhostCredentialsConnector(runnable)
        
        try:
            usernamePasswordCredentials = runnable.username and runnable.password
        except AttributeError:
            usernamePasswordCredentials = False
        try:
            pemCredentials = runnable.pemCertificate and runnable.pemKey
        except AttributeError:
            pemCredentials = False
        
        if usernamePasswordCredentials:
            return UsernamePasswordCredentialsConnector(runnable)
        if pemCredentials:
            return CertificateCredentialsConnector(runnable)
        
        raise ValueError('Missing credentials')

    @staticmethod
    def _useLocalHostCredentials(runnable):
        endpoint = getattr(runnable, 'endpoint', None)
        frontend = getattr(runnable, 'frontendIp', None)

        if AuthnFactory._isLocalhost(endpoint):
            return True
        if AuthnFactory._isLocalhost(frontend):
            return True
        return False

    @staticmethod
    def _isLocalhost(host):
        return (host == 'localhost' or host == '127.0.0.1')

class CredentialsConnector(object):

    def __init__(self, runnable):
        self.runnable = runnable
        self.pathPrefix = ''

    # used only for XMLRPC URL mangling
    def _manglePath(self, url):
        parts = url.split('/')
        return '/'.join(parts[0:-1]) + self.pathPrefix + parts[-1]

    def _insertUsernamePassword(self, url):
        protocolSeparator = '://'
        parts = url.split(protocolSeparator)
        quotedUsername = urllib.quote(self.username, '')
        quotedPassword = urllib.quote(self.password, '')
        return parts[0] + protocolSeparator + quotedUsername + ':' + quotedPassword + "@" + ''.join(parts[1:])
    
    def _validateUsernamePassword(self):
        if not self.username:
            raise ValidationException('Missing username')
        if not self.password:
            raise ValidationException('Missing password')

class UsernamePasswordCredentialsConnector(CredentialsConnector):
    
    def __init__(self, runnable):
        super(UsernamePasswordCredentialsConnector, self).__init__(runnable)
        self.username = runnable.username
        self.password = runnable.password
        self.pathPrefix = '/pswd/'
        self._validate()

    def _validate(self):
        return self._validateUsernamePassword()
    
    def createRpcConnection(self):
        url = self._insertUsernamePassword(self.runnable.cloud.server)
        url = self._manglePath(url)
        return xmlrpclib.ServerProxy(url)

    def createSessionString(self):
        return '%s:%s' % (self.username, self.password)


class CertificateCredentialsConnector(CredentialsConnector):
    
    class SafeTransportWithCert(xmlrpclib.SafeTransport):

        def __init__(self, cert, key):
            xmlrpclib.SafeTransport.__init__(self)
            self.__cert_file = cert
            self.__key_file = key

        def make_connection(self, host):
            host_with_cert = (host, {
                                     'key_file'  :  self.__key_file,
                                     'cert_file' :  self.__cert_file
                                     })
            return  xmlrpclib.SafeTransport.make_connection(self, host_with_cert)

    def __init__(self, runnable):
        super(CertificateCredentialsConnector, self).__init__(runnable)
        self.pemCertificate = runnable.pemCertificate
        self.pemKey = runnable.pemKey
        self.pathPrefix = '/cert/'
        self._validate()

    def _validate(self):
        if not os.path.exists(self.pemCertificate):
            raise ValueError('Can\'t find certificate file %s' % self.pemCertificate)
        
        if not os.path.exists(self.pemKey):
            raise ValueError('Can\'t find key file %s' % self.pemKey)
    
    def createRpcConnection(self):
        transport = CertificateCredentialsConnector.SafeTransportWithCert(self.pemCertificate, self.pemKey)
        url = self._manglePath(self.runnable.cloud.server)
        return xmlrpclib.ServerProxy(url, transport=transport)
    
    def createSessionString(self):
        return 'dummy:pass'


class LocalhostCredentialsConnector(CredentialsConnector):
    
    def __init__(self, runnable):
        super(LocalhostCredentialsConnector, self).__init__(runnable)
        self._setUsernamePassword(runnable)
        self._validate()
        
    def _validate(self):
        return self._validateUsernamePassword()
            
    def _setUsernamePassword(self, runnable):
        oneUsername = getattr(runnable, 'oneUsername', None)
        onePassword = getattr(runnable, 'onePassword', None)
        username = getattr(runnable, 'username', None)
        password = getattr(runnable, 'password', None)
        self.username = username or oneUsername
        self.password = password or onePassword
    
    def createRpcConnection(self):
        url = self._insertUsernamePassword('http://localhost:2633/RPC2')
        return xmlrpclib.ServerProxy(url)

    def createSessionString(self):
        return '%s:%s' % (self.username, self.password)


class UsernamePasswordCredentialsLoader(SimpleConfigParser):
    
    PASSWORD_INDEX = 0
    GROUP_INDEX = 1
     
    def __init__(self):
        super(UsernamePasswordCredentialsLoader, self).__init__()
        SimpleConfigParser.FILENAME = Defaults.AUTHN_CONFIG_FILE
        self.credentials = self.items

    def parse_value(self, value):
        parts = value.split(',')
        first = parts[0].strip()
        rest = ','.join(parts[1:]).strip()
        return (first, rest)
    
    def get_password(self, username):
        secrets = self._get_secrets(username)
        return secrets[UsernamePasswordCredentialsLoader.PASSWORD_INDEX]
            
    def get_group(self, username):
        secrets = self._get_secrets(username)
        return secrets[UsernamePasswordCredentialsLoader.GROUP_INDEX]
    
    def _get_secrets(self, username):
        try:
            return self.credentials[username]
        except KeyError:
            raise ValueError("No credentials for user: %s" % username)
