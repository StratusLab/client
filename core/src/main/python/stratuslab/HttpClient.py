import httplib2
from httplib2 import httplib
from stratuslab import Exceptions, Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ServerException, ClientException,\
    NetworkException

class HttpClient(object):

    def __init__(self, configHolder=ConfigHolder()):
        self.verboseLevel = None
        self.configHolder = configHolder
        configHolder.assign(self)        

    def get(self,url,accept='application/xml'):
        return self._httpCall(url,'GET',accept=accept)
        
    def post(self,url,body=None,contentType='application/xml',accept='application/xml'):
        return self._httpCall(url,'POST',body,contentType,accept)
    
    def _httpCall(self,url,method,body=None,contentType='application/xml',accept='application/xml',retry=True):
        
        def _convertContent(content):
            try:
                content = unicode(content,'utf-8')
            except:
                # If it fails (e.g. it's not a string-like media-type) ignore it
                pass
            return content
            
        
        def _handle3xx():
            if resp.status == 302:
                # Redirected
                resp, content = self.httpCall(resp['location'], method, body, accept)
            else:
                raise Exception('Should have been handled by httplib2!! ' + str(resp.status) + ": " + resp.reason)
            return resp, content

        def _handle4xx():
            raise ClientException(resp.reason)

        def _handle5xx():
            if retry:
                return self._httpCall(url, method, body, contentType, accept, False)
            raise ServerException('Failed calling method %s on url %s, with reason: %s' %
                                         (method, url, str(resp.status) + ": " + resp.reason))

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
        try:
            if len(headers):
                resp, content = h.request(url, method, body, headers=headers)
            else:
                resp, content = h.request(url, method, body)
        except httplib.BadStatusLine:
            raise NetworkException('Error: BadStatusLine contacting: ' + url)
        
        _handleResponse(resp, content)
        
        return resp, content

    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, 1)
