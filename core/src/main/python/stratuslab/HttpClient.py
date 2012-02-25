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

import httplib2
from httplib2 import httplib
from stratuslab import Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ServerException
from stratuslab.Exceptions import ClientException
from stratuslab.Exceptions import NetworkException

class HttpClient(object):

    def __init__(self, configHolder=ConfigHolder()):
        self.verboseLevel = None
        self.configHolder = configHolder
        self.crendentials = {}
        self.certificates = {}
        self.handleResponse = True
        configHolder.assign(self)        

    def get(self, url, accept='application/xml'):
        return self._httpCall(url, 'GET', accept=accept)
        
    def post(self, url, body=None, contentType='application/xml', accept='application/xml'):
        return self._httpCall(url, 'POST', body, contentType, accept, retry=False)
    
    def put(self, url, body=None, contentType='application/xml', accept='application/xml'):
        return self._httpCall(url, 'PUT', body, contentType, accept)
    
    def delete(self, url, body=None, contentType='application/x-www-form-urlencoded', accept='application/xml'):
        return self._httpCall(url, 'DELETE', body, contentType, accept)
    
    def head(self, url):
        return self._httpCall(url, 'HEAD')
    
    def addCredentials(self, username, password):
        self.crendentials[username] = password
        
    def addCertificate(self, key, cert):
        self.certificates[key] = cert
        
    def setHandleResponse(self, handle):
        self.handleResponse = handle
        
    def _addCredentials(self, http):
        for u, p in self.crendentials.items():
            http.add_credentials(u, p)
            
    def _addCertificate(self, http):
        for u, p in self.certificates.items():
            http.add_certificate(u, p, '')
    
    def _httpCall(self, url, method, body=None, contentType='application/xml', accept='application/xml', retry=True):
        
        def _convertContent(content):
            try:
                content = unicode(content, 'utf-8')
            except:
                # If it fails (e.g. it's not a string-like media-type) ignore it
                pass
            return content
            
        
        def _handle3xx():
            if resp.status == 302:
                # Redirected
                resp, content = self._httpCall(resp['location'], method, body, accept)
            else:
                raise Exception('Should have been handled by httplib2!! ' + str(resp.status) + ": " + resp.reason)
            return resp, content

        def _handle4xx():
            raise ClientException('Failed calling method %s on url %s, with reason: %s' %
                                  (method, url, str(resp.status) + ": " + resp.reason),
                                  content=content,
                                  status=str(resp.status))

        def _handle5xx():
            if retry:
                return self._httpCall(url, method, body, contentType, accept, False)
            raise ServerException('Failed calling method %s on url %s, with reason: %s' % 
                                         (method, url, str(resp.status) + ": " + resp.reason), 
                                         status=str(resp.status))

        def _handleResponse(resp, content):
            self._printDetail('Received response: %s' % resp + \
                             '\nwith content:\n %s' % \
                             _convertContent(content))

            if str(resp.status).startswith('2'):
                return resp, content
            
            if str(resp.status).startswith('3'):
                resp, content = _handle3xx()
            
            if str(resp.status).startswith('4'):
                resp, content = _handle4xx()

            if str(resp.status).startswith('5'):
                resp, content = _handle5xx()

        h = httplib2.Http(".cache")
        h.force_exception_to_status_code = False
        self._printDetail('Contacting the server with %s, at: %s' % (method, url))
        headers = {}
        if contentType:
            headers['Content-Type'] = contentType
        if accept:
            headers['Accept'] = accept
        self._addCredentials(h)
        self._addCertificate(h)
        try:
            if len(headers):
                resp, content = h.request(url, method, body, headers=headers)
            else:
                resp, content = h.request(url, method, body)
        except httplib.BadStatusLine:
            raise NetworkException('BadStatusLine when contacting ' + url)
        except AttributeError:
            raise NetworkException('Cannot contact ' + url)
        
        if self.handleResponse:
            try:
                _handleResponse(resp, content)
            except ClientException, ex:
                ex.mediaType = headers['Accept']
                raise

        return resp, content

    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, 1)
