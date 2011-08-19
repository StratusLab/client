#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Centre National de la Recherche Scientifique (CNRS)
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
import unittest
import time
import random
import string

import pika
from pika.adapters import BlockingConnection

class NotificationUseCaseTest(unittest.TestCase):

    queue = 'stratuslab-' + str(random.randint(10000, 99999))

    username = 'guest'
    password = 'guest'

    amqp = {
        'host' : 'dev.rabbitmq.com',
        'port' : 5672,
        'virtual_host' : '/',
        'credentials' : pika.PlainCredentials(username, password)
        }

    machineStates = [ 'CREATED', 'RUNNING', 'DONE' ]

    maxSecondsToWait = 10

    def createMsgRecipients(self):
        option = string.join( 
            [self.amqp['host'],
            self.amqp['virtual_host'],
            self.username,
            self.password,
            self.queue],
            ',')
        return [option]


    def initializeMessageQueue(self):

        # Connect to RabbitMQ
        parameters = pika.ConnectionParameters(**self.amqp)
        connection = BlockingConnection(parameters)
        
        # Open the channel
        channel = connection.channel()
        
        # Declare the queue
        channel.queue_declare(queue=self.queue, 
                              durable=False,
                              exclusive=True, 
                              auto_delete=True)

        print 'Queue: %s' % self.queue

        return (connection, channel)


    def checkNotificationMessages(self, connection, vmId):

        expectedMessages = {}
        for state in self.machineStates:
            message = 'VMID=%i; STATE=%s' % (vmId, state)
            expectedMessages[message] = 1

        channel = connection.channel()

        timedOut = False
        startTime = time.time()
        while len(expectedMessages) > 0 and not timedOut:

            # Call basic get which returns the 3 frame types
            method_frame, header_frame, body = channel.basic_get(queue=self.queue)
            
            # It can be empty if the queue is empty so don't do anything
            if not method_frame.NAME == 'Basic.GetEmpty':
                print "Basic.GetOk %s delivery-tag %i: %s" % (
                    header_frame.content_type,
                    method_frame.delivery_tag,
                    body)
                
                # Acknowledge the receipt of the data
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)

                # Remove message from list of expected messages.
                try:
                    del(expectedMessages[body])
                except KeyError:
                    print 'Unexpected message: %s' % body

            # Don't pound the message server.
            time.sleep(1)                

            # Determine if we've timed out.
            timedOut = (time.time() - startTime) > self.maxSecondsToWait

        if len(expectedMessages) > 0 :
            self.assertEquals(0, len(expectedMessages), 
                              'Unreceived messages:  ' + str(expectedMessages.keys()))


    def cleanUpMessageQueue(self, connection):
        if not connection:
            connection.close()


    def testDummy(self):
        pass


if __name__ == "__main__":
    unittest.main()

