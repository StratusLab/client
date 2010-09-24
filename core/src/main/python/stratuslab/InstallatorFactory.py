from stratuslab.installator import one

class InstallatorFactory(object):
    
    def getInstallator(self, **kw):
        return one.OneInstallator(**kw)
    