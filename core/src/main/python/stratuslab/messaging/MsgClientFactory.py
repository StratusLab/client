
def getMsgClient(configHolder):
    MsgClientFactory(configHolder).getClient()

class MsgClientFactory(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.configHolder = configHolder

    def getClient(self):
        msg_type = self.configHolder.msg_type.lower()

        if msg_type == 'amazonsqs':
            from stratuslab.messaging.AmazonSqsQueue import AmazonSqsQueue
            AmazonSqsQueue(self.configHolder)
        elif msg_type == 'rest':
            from stratuslab.messaging.RestPublisher import RestPublisher
            return RestPublisher(self.configHolder)
        elif msg_type == 'dirq':
            from stratuslab.messaging.DirectoryQueue import DirectoryQueue
            return DirectoryQueue(self.configHolder)
        else:
            raise Exception('Unknown messaging client type: %s' % msg_type)
