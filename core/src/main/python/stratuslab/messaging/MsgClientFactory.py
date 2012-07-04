from .Defaults import MSG_CLIENTS

def getMsgClient(configHolder):
    return MsgClientFactory(configHolder).getClient()

class MsgClientFactory(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.configHolder = configHolder

    def getClient(self):
        msg_type = self.configHolder.msg_type.lower()

        if msg_type not in MSG_CLIENTS.keys():
            raise Exception('Unknown messaging client type: %s' % msg_type)

        MsgClient = None
        exec "from stratuslab.messaging.%(msg_client)s import %(msg_client)s as MsgClient" % \
                                            {'msg_client': MSG_CLIENTS[msg_type]}
        return MsgClient(self.configHolder)
