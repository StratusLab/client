import sys
import time

import os
import subprocess
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
    filePutContent(savePath, fd.read())
    fd.close()
    
def ping(host, timeout=5, number=1, ** kwargs):
    '''Ping <host> and return True if successful'''
    p = subprocess.Popen(['ping', '-q', '-c', str(number), '-W', str(timeout), host], ** kwargs)
    p.wait()
    return p.returncode == 0

def appendOrReplaceInFile(filename, search, replace):
    if not os.path.isfile(filename):
        filePutContent(filename, replace)
        return 
    
    fileContent = fileGetContent(filename)
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
    
    filePutContent(filename, '\n'.join(newContent))

def fileGetContent(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content

def filePutContent(filename, data):
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

    h = shaMethod(string)
    return h.hexdigest()

def waitUntilPingOrTimeout(host, timeout, ticks=True, stdout=None, stderr=None):
    if not stdout:
        stdout = open('/dev/null', 'w')
    if not stderr:
        stderr = open('/dev/null', 'w')
    
    start = time.time()
    retCode = False
    while not retCode:
        if ticks:
            sys.stdout.flush()
            sys.stdout.write('.')
        retCode = ping(host, stdout=stdout, stderr=stderr)
        time.sleep(1)
        
        if time.time() - start > timeout:
            return False
        
    return retCode == 0

def setPythonPath(path):
    if not path in sys.path:
        sys.path.append(path)

def printAction(msg):
    sys.stdout.flush()
    print ('\n> %s' % msg),
    
def printStep(msg):
    sys.stdout.flush()
    print ('\n :: %s' % msg),

def printError(msg, exitCode=1, exit=True):
    sys.stdout.flush()
    print ('\n  ** %s' % msg),
    
    if exit:
        sys.exit(exitCode)
    