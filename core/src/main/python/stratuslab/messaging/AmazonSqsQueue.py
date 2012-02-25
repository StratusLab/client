import base64
import httplib
import urllib

SECRET_HEADER = {'User-Agent':'StratusLab'}

class AmazonSqsQueue(object):
    def __init__(self, configHolder):
        configHolder.assign(self)
        self.conn = httplib.HTTPSConnection(self.msg_endpoint)
        self.conn.debuglevel = self.verboseLevel
        self.headers = {'Accept':'*/*', 
                        'Content-Type':'application/x-www-form-urlencoded'}
        self.headers.update(SECRET_HEADER)

    @staticmethod
    def _endcode_message(message):
        return base64.b64encode(message)
    def _build_query_params(self, message):
        params = {'Action':'SendMessage',
                  'MessageBody':self._endcode_message(message)}
        return urllib.urlencode(params)

    def send(self, message):
        'message - dictionary'
        params = self._build_query_params(message)
        self.conn.request('POST', self.msg_queue, params, self.headers)
        response = self.conn.getresponse()
        status = str(response.status)
        if not status.startswith('2'):
            data = response.read()
            raise Exception(data)
        self.conn.close()
