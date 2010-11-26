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
        usernamePasswordCredentials = runnable.username and runnable.password
        pemCredentials = runnable.pemCert and runnable.pemKey
        
        if pemCredentials:
            return CertificateCredentialsConnector(runnable)
        if usernamePasswordCredentials:
            return UsernamePasswordCredentialsConnector(runnable)
        
        raise ValueError('Unknown Credentials for runnable')

class CredentialsConnector(object):

    def __init__(self, runnable):
        self.runnable = runnable

class UsernamePasswordCredentialsConnector(CredentialsConnector):
    
    def __init__(self, runnable):
        super(UsernamePasswordCredentialsConnector, self).__init__(runnable)
        self.certFile = None
        self.keyFile = None
    
    def createRpcConnection(self):
        return xmlrpclib.ServerProxy(self.runnable.cloud.server)

    def createSessionString(self):
        return '%s:%s' % (self.runnable.username, Util.shaHexDigest(self.runnable.password))


class CertificateCredentialsConnector(CredentialsConnector):
    
    class SafeTransportWithCert(xmlrpclib.SafeTransport):

        def __init__(self, cert, key):
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
    
    def createRpcConnection(self):
        transport = CertificateCredentialsConnector.SafeTransportWithCert(self.runnable.pemCert, self.runnable.pemKey)
        return xmlrpclib.ServerProxy(self.runnable.cloud.server, transport=transport)
    
    def createSessionString(self):
        return 'dummy:pass'
