from stratuslab.cloud import one
from stratuslab.cloud import qemu

class CloudConnectorFactory:
    
    def getCloud(self):
        return one.OneConnector()

    def getDummyCloud(self):
        return qemu.QEmuConnector()
    