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
import json

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.CommandBase import CommandBaseSysadmin
from stratuslab.messaging.Defaults import MSG_TYPES
from stratuslab.messaging.MsgClientFactory import getMsgClient

class MessagingCommand(CommandBaseSysadmin):

    def __init__(self):
        self.msg_message = ''
        super(MessagingCommand, self).__init__()

    @staticmethod
    def set_imageid(message, imageid):
        'message - JSON and can be base64 encoded'
        if not message.startswith('{'):
            # Assume this is base64 encoded message.
            message = base64.b64decode(message)
        try:
            message_dict = json.loads(message)
        except Exception, ex:
            raise ValueError("Couldn't load JSON message: %s" %  str(ex))
        message_dict['imageid'] = imageid
        return json.dumps(message_dict)

    def parse(self):
        self.parser.usage = '%prog [options] message'

        self.parser.add_option('--msg-type', dest='msg_type',
                    help='Type of messaging: %s. Mandatory.' % ', '.join(MSG_TYPES), 
                    metavar='NAME', default="")
        self.parser.add_option('--msg-endpoint', dest='msg_endpoint',
                    help='Messaging service endpoint. Mandatory.', 
                    metavar='ENDPOINT', default="")
        self.parser.add_option('--msg-queue', dest='msg_queue',
                    help='Message queue name. Mandatory.', metavar='NAME',
                    default="")
        self.parser.add_option('--imageid', dest='imageid',
                    help='Image ID. Assumes message is JSON representation '
                    'of a dictionary on which the ID will be set. JSON can be '
                    'base64 encoded.', metavar='ID',
                    default="")

        self.options, self.args = self.parser.parse_args()

    def checkOptions(self):
        super(MessagingCommand, self).checkOptions()

        if not self.options.msg_type:
            self.printMandatoryOptionError('--msg-type')
        if not self.options.msg_endpoint:
            self.printMandatoryOptionError('--msg-endpoint')
        if not self.options.msg_queue:
            self.printMandatoryOptionError('--msg-queue')

        self._checkMessageAndImageid()

    def _checkMessageAndImageid(self):
        if len(self.args) != 0:
            self.msg_message = self.args[0]
        else:
            self.printError('Message should be set as first argument')

        # We are publishing image ID. Set image ID in the message.
        if self.options.imageid:
            self.msg_message = MessagingCommand.set_imageid(self.msg_message,
                                                       self.options.imageid)

    def _getMessage(self):
        if self.options.msg_type.lower() == 'rest' and self.options.imageid:
            message = self.options.imageid
        else:
            message = self.msg_message
        return message

    def sendMessage(self):
        config = ConfigHolder.configFileToDict(self.options.configFile) 
        configHolder = ConfigHolder(self.options.__dict__, config)

        client = getMsgClient(configHolder)
        message = self._getMessage()
        client.send(message)
