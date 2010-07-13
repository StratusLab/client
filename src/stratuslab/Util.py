import os
import urllib2

from ConfigParser import SafeConfigParser

defaultConfigSection = 'stratuslab'

def parseConfig(configFile):
    if not os.path.isfile(configFile):
        raise ValueError('Configuration file %s does not exists' %
            configFile)

    config = SafeConfigParser()
    config.read(configFile)    
    validConfiguration(config)
    return dict(config.items(defaultConfigSection))

def fileGetContents(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content

def filePutContents(filename, data):
    fd = open(filename, 'wb')
    fd.write(data)
    fd.close()

def validConfiguration(config):
    if not config.has_section(defaultConfigSection):
        raise ValueError('Invalid configuration')

def wget(url, savePath):
    fd = urllib2.urlopen(url)
    filePutContents(savePath, fd.read())
    fd.close()
        
