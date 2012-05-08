
class AmqpClient(object):
    def __init__(self, configHolder):
        configHolder.assign(self)

    def send(self, message):
        raise NotImplementedError()
