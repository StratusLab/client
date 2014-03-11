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
import json
import stat
import base64
import mimetools
import mimetypes
import httplib2
import ssl
from httplib2 import httplib
from time import gmtime, strftime
from stratuslab import Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ServerException
from stratuslab.Exceptions import ClientException
from stratuslab.Exceptions import NetworkException

class HttpClient(object):

    ENV_HTTP_PROXY = 'http_proxy'
    ENV_NO_PROXY = 'no_proxy'

    @staticmethod
    def getHttpProxyForUrl(url):
        proxy = None
        url_host = Util.parseUri(url)[1]
        envProxy = HttpClient._getEnvVarProxy()
        if envProxy and not (url_host in HttpClient._getEnvVarNoProxy()):
            proxy_server, proxy_port = Util.parseUri(envProxy)[1:3]
            proxy = httplib2.ProxyInfo(3, proxy_server, int(proxy_port), 
                                       proxy_rdns=True)
        return proxy

    @staticmethod
    def _getEnvVarProxy():
        return os.environ.get(HttpClient.ENV_HTTP_PROXY)
    @staticmethod
    def _getEnvVarNoProxy():
        return os.environ.get(HttpClient.ENV_NO_PROXY)

    def __init__(self, configHolder=ConfigHolder()):
        self.verboseLevel = None
        self.configHolder = configHolder
        self.crendentials = {}
        self.certificates = {}
        self.handleResponse = True
        self.useHttpCache = False
        configHolder.assign(self)

    def get(self, url, accept='application/xml'):
        return self._httpCall(url, 'GET', accept=accept)

    def post(self, url, body=None, contentType='application/xml', accept='application/xml'):
        return self._httpCall(url, 'POST', body, contentType, accept, retry=False)

    def post_multipart(self, url, files=[], params=[], accept='application/xml'):
        boundary, body = self._multipart_encode(files, params)
        contentType = 'multipart/form-data; boundary=%s' % boundary
        return self.post(url, body, contentType=contentType, accept=accept)

    def _multipart_encode(self, files, params):
        "files - list of (<attribute name>, <file descriptor>) tuples"
        "params - list of (<attribute name>, <value>) tuples"
        boundary = mimetools.choose_boundary()
        body = ''
        for(key, value) in params:
            body += '--%s\r\n' % boundary
            body += 'Content-Disposition: form-data; name="%s"' % key
            body += '\r\n\r\n' + value + '\r\n'
        for(key, fh) in files:
            file_size = os.fstat(fh.fileno())[stat.ST_SIZE]
            filename = fh.name.split('/')[-1]
            contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            body += '--%s\r\n' % boundary
            body += 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename)
            body += 'Content-Type: %s\r\n' % contenttype
            body += 'Content-Length: %s\r\n' % file_size
            fh.seek(0)
            body += '\r\n' + fh.read() + '\r\n'
            fh.close()
        body += '--%s--\r\n\r\n' % boundary
        return boundary, body

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

    def _addCredentialsToHeader(self, headers):
        if self.crendentials:
            u, p = self.crendentials.items()[0]
            headers['authorization'] = 'Basic ' + base64.b64encode('%s:%s' % (u, p))
            return headers

    def _addCertificate(self, http):
        for u, p in self.certificates.items():
            http.add_certificate(u, p, '')

    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, Util.VERBOSE_LEVEL_DETAILED)

    # This is a bandaid for problems associated with dropped SSL handshakes.  The
    # root cause of these problems needs to be found and fixed.
    def _retryHttpRequestOnSSLError(self, httpObject, url, method, body, headers):
        maxRetries = 3
        retries = 0
        lastException = None
        while retries < maxRetries:
            try:
                if len(headers):
                    return httpObject.request(url, method, body, headers=headers)
                else:
                    return httpObject.request(url, method, body)
            except ssl.SSLError as e:
                t = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                self._printDetail('SSL ERROR ENCOUNTERED (%s): %s' % (t, str(e)))
                lastException = e
                retries += 1
            except httplib2.ssl_SSLError as e:
                t = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                self._printDetail('SSL ERROR ENCOUNTERED (%s): %s' % (t, str(e)))
                lastException = e
                retries += 1

        raise lastException

    def _httpCall(self, url, method, body=None, contentType='application/xml', accept='application/xml', retry=True):

        def _convertContent(content):

            size = len(content)
            if size > 2048:
                return '<content too large; %d bytes>' % size

            try:
                return unicode(content, 'utf-8')
            except:
                return '<non-text content>'

        def _getErrorMessageFromJsonContent(content):
            try:
                return json.loads(content)['message']
            except:
                return ''

        def _handle3xx(resp):
            if resp.status == 302:
                # Redirected
                resp, content = self._httpCall(resp['location'], method, body, accept)
            else:
                raise Exception('Should have been handled by httplib2!! ' + str(resp.status) + ": " + resp.reason)
            return resp, content

        def _handle4xx(resp):
            error_message = _getErrorMessageFromJsonContent(content)
            raise ClientException('Failed calling method %s on url %s, with reason: %s. Error: %s' %
                                  (method, url, str(resp.status) + ": " + resp.reason, error_message),
                                  content=content,
                                  status=str(resp.status))

        def _handle5xx(resp):
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
                resp, content = _handle3xx(resp)

            if str(resp.status).startswith('4'):
                resp, content = _handle4xx(resp)

            if str(resp.status).startswith('5'):
                resp, content = _handle5xx(resp)

        proxy = self.getHttpProxyForUrl(url)
        if Util.isTrueConfVal(self.useHttpCache):
            h = httplib2.Http(".cache", proxy_info=proxy)
        else:
            h = httplib2.Http(proxy_info=proxy)
        h.force_exception_to_status_code = False
        h.disable_ssl_certificate_validation=True
        self._printDetail('Contacting the server with %s, at: %s' % (method, url))
        headers = {}
        if contentType:
            headers['Content-Type'] = contentType
        if accept:
            headers['Accept'] = accept
        # See https://github.com/StratusLab/client/issues/8
        if method == 'POST':
            self._addCredentialsToHeader(headers)
        self._addCredentials(h)
        self._addCertificate(h)
        try:
            resp, content = self._retryHttpRequestOnSSLError(h, url, method, body, headers)
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
