
import stomp

STOMP_PORT = '61613'

class StompClient(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.destination = self.msg_queue
        
        host, port = self.msg_endpoint.split(':')
        port = port or STOMP_PORT

        self.connection = stomp.Connection(host_and_ports = [(host, int(port))])

    def send(self, message):
        raise NotImplementedError()
