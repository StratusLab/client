from stratuslab import Exceptions

INSTALLERS = ('yum', 'apt')

yumOsList = ('centos', 'fedora', 'sl', 'scientificlinux')
aptOsList = ('ubuntu')

def getInstallerBasedOnOs(os):
    if os in yumOsList:
        return 'yum'
    elif os in aptOsList:
        return 'apt'
    else:
        raise Exceptions.ExecutionException('Unsupported OS: %s' % os)

packageAndVersionSeparators = {'yum' : '-',
                               'apt' : '='}

def getPackageAndVersionSeparatorBasedOnOs(os):
    return packageAndVersionSeparators[getInstallerBasedOnOs(os)]
