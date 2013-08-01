#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, SixSq Sarl
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

import base64
import httplib2
import urllib

from stratuslab.HttpClient import HttpClient
from stratuslab.messaging.MsgBase import MsgBase

SECRET_HEADER = {'User-Agent':'StratusLab'}

class AmazonSqsQueue(MsgBase):
    def __init__(self, configHolder):
        super(AmazonSqsQueue, self).__init__(configHolder)
        self.conn = httplib2.Http(
                    proxy_info=HttpClient.getHttpProxyForUrl(self.msg_endpoint))
        self.conn.force_exception_to_status_code = False
        self.conn.disable_ssl_certificate_validation=True
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
        url = self.msg_endpoint + '/' + self.msg_queue.strip('/')
        url_params = '%s?%s' % (url, self._build_query_params(message))
        response, content = self.conn.request(url_params, 'POST', 
                                              headers=self.headers)
        status = str(response.status)
        if not status.startswith('2'):
            raise Exception('HTTP call failed with ' + str(status))
