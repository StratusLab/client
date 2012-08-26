
import unittest

from stratuslab.messaging.MsgClientFactory import getMsgClient
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.messaging.Defaults import MSG_CLIENTS

class MsgClientTest(unittest.TestCase):

    def xtest_TEST(self):
        from stratuslab.messaging.EmailClient import EmailClient
        
        email = MIMEMultipart()
        EmailClient._compose_email = Mock(return_value=email)
        EmailClient._send_email = Mock()

        tm._sendEmailToUser()

        EmailClient._send_email.assert_called_once_with(email)
