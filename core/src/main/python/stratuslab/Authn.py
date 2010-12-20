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
import xmlrpclib

import Util


class AuthnFactory(object):
    
    @staticmethod
    def getCredentials(runnable):
        try:
            usernamePasswordCredentials = runnable.username and runnable.password
        except AttributeError:
            usernamePasswordCredentials = False
        try:
            pemCredentials = runnable.pemCert and runnable.pemKey
        except AttributeError:
            pemCredentials = False
        
        if pemCredentials:
            return CertificateCredentialsConnector(runnable)
        if usernamePasswordCredentials:
            return UsernamePasswordCredentialsConnector(runnable)
        
        raise ValueError('Missing credentials')

class CredentialsConnector(object):

    def __init__(self, runnable):
        self.runnable = runnable
        self.pathPrefix = ''

    def _manglePath(self, url):
        parts = url.split('/')
        return '/'.join(parts[0:-1]) + self.pathPrefix + parts[-1]

class UsernamePasswordCredentialsConnector(CredentialsConnector):
    
    def __init__(self, runnable):
        super(UsernamePasswordCredentialsConnector, self).__init__(runnable)
        self.username = runnable.username
        self.password = runnable.password
        self.pathPrefix = '/pswd/'        
    
    def createRpcConnection(self):
        url = self._insertUsernamePassword(self.runnable.cloud.server)
        url = self._manglePath(url)
        return xmlrpclib.ServerProxy(url)

    def _insertUsernamePassword(self, url):
        protocolSeparator = '://'
        parts = url.split(protocolSeparator)
        return parts[0] + protocolSeparator + self.username + ':' + self.password + "@" + ''.join(parts[1:])

    def createSessionString(self):
        return '%s:%s' % (self.username, Util.shaHexDigest(self.password))


class CertificateCredentialsConnector(CredentialsConnector):
    
    class SafeTransportWithCert(xmlrpclib.SafeTransport):

        def __init__(self, cert, key):
            xmlrpclib.SafeTransport.__init__(self)
            self.__cert_file = cert
            self.__key_file  = key

        def make_connection(self, host):
            host_with_cert = (host, {
                                     'key_file'  :  self.__key_file,
                                     'cert_file' :  self.__cert_file
                                     } )
            return  xmlrpclib.SafeTransport.make_connection(self, host_with_cert)

    def __init__(self, runnable):
        super(CertificateCredentialsConnector, self).__init__(runnable)
        self.pemCert = runnable.pemCert
        self.pemKey = runnable.pemKey
        self.pathPrefix = '/cert/'
    
    def createRpcConnection(self):
        transport = CertificateCredentialsConnector.SafeTransportWithCert(self.pemCert, self.pemKey)
        url = self._manglePath(self.runnable.cloud.server)
        return xmlrpclib.ServerProxy(url, transport=transport)
    
    def createSessionString(self):
        return 'dummy:pass'
