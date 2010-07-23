import os
import urllib2

from ConfigParser import SafeConfigParser

defaultConfigSection = 'stratuslab'


def validateConfig(config):
    if not config.has_section(defaultConfigSection):
        raise ValueError('Invalid configuration')

def parseConfig(configFile):
    if not os.path.isfile(configFile):
        raise ValueError('Configuration file %s does not exists' %
            configFile)

    config = SafeConfigParser()
    config.read(configFile)    
    validateConfig(config)
    return dict(config.items(defaultConfigSection))

def wget(url, savePath):
    fd = urllib2.urlopen(url)
    filePutContents(savePath, fd.read())
    fd.close()

def appendOrReplaceInFile(filename, search, replace):
    if not os.path.isfile(filename):
        filePutContents(filename, replace)
        return 
    
    fileContent = fileGetContents(filename)
    lines = fileContent.split('\n')
    
    newContent = []
    insertionMade = False
    for line in lines:
        if line.startswith(search):
            newContent.append(replace)
            insertionMade = True
        else:
            newContent.append(line)
    
    if insertionMade is False:
        newContent.append('%s\n' % replace)
    
    filePutContents(filename, '\n'.join(newContent))

def fileGetContents(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content

def filePutContents(filename, data):
    fd = open(filename, 'wb')
    fd.write(data)
    fd.close()
        
def shaHexDigest(string):
    shaMethod = None
    try:
        import hashlib
        shaMethod = hashlib.sha1
    except:
        import sha
        shaMethod = sha.new

    shaMethod(string)
    return shaMethod.hexdigest()
    