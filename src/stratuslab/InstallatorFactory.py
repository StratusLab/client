from stratuslab.installator import one

class InstallatorFactory(object):
    
    def getInstallator(self):
        return one.OneInstallator()
    