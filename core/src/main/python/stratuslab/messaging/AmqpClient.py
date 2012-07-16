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

import pika

from stratuslab.messaging.MsgBase import MsgBase

class AmqpClient(MsgBase):
    def __init__(self, configHolder):
        super(AmqpClient, self).__init__(configHolder)
        
        self.connection = None
        self.connection_params = pika.ConnectionParameters(self.msg_endpoint)
        
    def connect(self):
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        
    def send(self, message):
        self.channel.queue_declare(queue=self.msg_queue)
        self.channel.basic_publish(exchange='',
                                   routing_key=self.msg_queue,
                                   body=message)

    def disconnect(self):
        self.connection.close()
