from stratuslab.cloud import one

class CloudConnectorFactory:
    
    def getCloud(self):
        return one.OneConnector()
    