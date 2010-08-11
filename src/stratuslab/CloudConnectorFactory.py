from stratuslab.cloud import one
from stratuslab.cloud import qemu

class CloudConnectorFactory:

    @staticmethod
    def getCloud(type='one'):
        if type == 'one':
            return one.OneConnector()
        elif type == 'qemu':
            return qemu.QEmuConnector()
        else:
            raise NotImplementedError('Cloud type not implemented yet.')
