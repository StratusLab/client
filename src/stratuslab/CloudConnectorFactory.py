from stratuslab.cloud import one
from stratuslab.cloud import qemu

class CloudConnectorFactory:
    
    def getCloud(self, type='one'):
        if type == 'one':
            return one.OneConnector()
        elif type == 'dummy':
            return qemu.QEmuConnector()
        else:
            raise NotImplementedError('Cloud type not implemented yet.')
