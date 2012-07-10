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

import time
import stomp

from stratuslab.messaging.MsgBase import MsgBase

STOMP_PORT = '61613'

class StompClient(MsgBase):
    def __init__(self, configHolder):
        super(StompClient, self).__init__(configHolder)
        
        port = STOMP_PORT
        try:
            host, port = self.msg_endpoint.split(':')
        except ValueError:
            host = self.msg_endpoint

        self.connection = stomp.Connection(host_and_ports=[(host, int(port))])

    def connect(self):
        self.connection.start()
        self.connection.connect()

    def send(self, message):
        if not self.connection.connected:
            self.connect()

        self.connection.subscribe(destination=self.msg_queue, ack='auto')
        self.connection.send(message, destination=self.msg_queue)

    def disconnect(self):
        self.connection.disconnect()
