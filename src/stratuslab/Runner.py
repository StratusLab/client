
class Runner(object):

    def __init__(self, image, options, config):
        self.image = image
        self.config = config
        self.instanceNumber = options.instanceNumber
        self.instanceType = options.instanceType
        self.userKey = options.userKey

    @staticmethod
    def getInstanceType():
        types = {
            # name      :   (cpu, ram, swap)
            'm1.small'  :   (1, 128, 1024),
            'c1.medium' :   (1, 256, 1024),
            'm1.large'  :   (2, 512, 1024),
            'm1.xlarge' :   (2, 1024, 1024),
            'c1.xlarge' :   (4, 2048, 2048),
        }
        return types

    def runInstance(self):
        pass