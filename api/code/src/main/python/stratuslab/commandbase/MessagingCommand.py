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

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.CommandBase import CommandBaseSysadmin
from stratuslab.messaging.Defaults import MSG_TYPES
from stratuslab.messaging.Defaults import MSG_SMTP_HOST
from stratuslab.messaging.MessagePublishers import ImageIdPublisher, SingleMessagePublisher
from stratuslab.image.Image import Image
from stratuslab.Exceptions import ValidationException


class MessagingCommand(CommandBaseSysadmin):
    def __init__(self):
        self.msg_message = ''
        super(MessagingCommand, self).__init__()

    def parse(self):
        self.parser.usage = '%prog [options] message'

        self.parser.description = '''
Send the given message to the given messaging server.
'''

        self.parser.add_option('--msg-type', dest='msg_type',
                               help='Type of messaging: %s. Mandatory.' % ', '.join(MSG_TYPES),
                               metavar='NAME', default="")
        self.parser.add_option('--msg-endpoint', dest='msg_endpoint',
                               help='Messaging service endpoint. Mandatory.',
                               metavar='ENDPOINT', default="")
        self.parser.add_option('--msg-queue', dest='msg_queue',
                               help='Message queue name. Mandatory.', metavar='NAME',
                               default="")
        self.parser.add_option('--msg-smtp-host', dest='smtp_host',
                               help="SMTP relay hostname to be used with 'email' messaging "
                                    "type. Default: %s" % MSG_SMTP_HOST,
                               metavar='HOSTNAME', default=MSG_SMTP_HOST)
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

        if self.options.imageid:
            if not Image.isImageId(self.options.imageid):
                raise ValidationException('Marketplace image ID is expected.')

    def sendMessage(self):
        config = ConfigHolder.configFileToDict(self.options.configFile)
        configHolder = ConfigHolder(self.options.__dict__, config)

        if self.options.imageid:
            ImageIdPublisher(self.msg_message,
                             self.options.imageid, configHolder).publish()
        else:
            SingleMessagePublisher(self.msg_message, configHolder).publish()
