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
import httplib
import urllib

from stratuslab.messaging.MsgBase import MsgBase

SECRET_HEADER = {'User-Agent':'StratusLab'}

class AmazonSqsQueue(MsgBase):
    def __init__(self, configHolder):
        super(AmazonSqsQueue, self).__init__(configHolder)

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
