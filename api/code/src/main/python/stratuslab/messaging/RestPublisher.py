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

import json
import commands

from stratuslab.Util import printWarning
from stratuslab.messaging.MsgBase import MsgBase
from stratuslab.HttpClient import HttpClient

class _RestPublisherHttpClient(MsgBase):
    def __init__(self, configHolder):
        self.restEndpoints = '{}'
        super(_RestPublisherHttpClient, self).__init__(configHolder)

        self.resource = '%s/%s' % (self.msg_endpoint, self.msg_queue)
        self.httpClient = HttpClient(configHolder)
        self._assignCredentials()

    def _assignCredentials(self):
        endpts_creds = json.loads(self.restEndpoints)
        try:
            creds = endpts_creds[self.msg_endpoint]
        except KeyError:
            printWarning('WARNING: no matching credentials for ' + self.msg_endpoint)
        else:
            self.httpClient.addCredentials(creds['username'], creds['password'])

    def send(self, message):
        self.httpClient.put(self.resource, message)

class _RestPublisherCurl(MsgBase):
    def __init__(self, configHolder):
        self.restEndpoints = '{}'
        super(_RestPublisherCurl, self).__init__(configHolder)

        self.resource = '%s/%s' % (self.msg_endpoint, self.msg_queue)
        self._assignCredentials()

    def _assignCredentials(self):
        endpts_creds = json.loads(self.restEndpoints)
        try:
            creds = endpts_creds[self.msg_endpoint]
        except KeyError:
            printWarning('WARNING: no matching credentials for ' + self.msg_endpoint)
        else:
            self.username = creds['username']
            self.password = creds['password']

    def send(self, message):
        user = ''
        if self.username and self.password:
            user = '--user %s:%s' % (self.username, self.password)
        cmd = 'curl -d %s -X PUT %s %s' % (message, user, self.resource)
        rc, output = commands.getstatusoutput(cmd)
        if rc != 0 or ('Error' in output):
            raise Exception("Command : %s\nFailed with :\n%s" % (cmd, output))

# FIXME: RestPublisherHttpClient.send() fails at the moment
RestPublisher = _RestPublisherCurl
