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

import os

from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

from stratuslab.messaging.MsgBase import MsgBase
from stratuslab.messaging.Defaults import MSG_SENDER_EMAIL
from stratuslab.messaging.Defaults import MSG_SMTP_HOST

class EmailClient(MsgBase):
    def __init__(self, configHolder):
        self.smtp_host = MSG_SMTP_HOST
        self.subject = ''
        self.recipient = ''
        self.sender = ''

        super(EmailClient, self).__init__(configHolder)
        
        self.subject = self.subject or self.msg_queue
        self.recipient = self.recipient or self.msg_endpoint
        self.sender = self.sender or MSG_SENDER_EMAIL

    def send(self, message, attachment=''):
        email = self._compose_email(message, attachment)

        self._send_email(email)
    
    def _compose_email(self, message, attachment):
        email = MIMEMultipart()
        email['Subject'] = self.subject
        email['From'] = self.sender
        email['To'] = self.recipient
        email.attach(MIMEText(message))

        if attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(open(attachment, 'rb').read())
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % 
                                os.path.basename(attachment))
            email.attach(part)

        return email

    def _send_email(self, email):
        smtp = SMTP(self.smtp_host)
        smtp.sendmail(self.sender,
                      self.recipient,
                      email.as_string())
        smtp.quit()
