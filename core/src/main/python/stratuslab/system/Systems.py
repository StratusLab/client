from stratuslab import Exceptions

INSTALLERS = ('yum', 'apt')

yumOsList = ('centos', 'fedora')
aptOsList = ('ubuntu')

def getInstallerBasedOnOs(os):
    if os in yumOsList:
        return 'yum'
    elif os in aptOsList:
        return 'apt'
    else:
        raise Exceptions.ExecutionException('Unsupported OS: %s' % os)
