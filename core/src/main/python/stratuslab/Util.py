#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os.path
import re
import subprocess
import sys
import time
import urllib2
from random import sample
from string import ascii_lowercase
from Exceptions import ImportException


defaultRepoConfigSection = 'stratuslab_repo'
defaultRepoConfigPath = '.stratuslab/stratuslab.repo.cfg'
modulePath = os.path.abspath('%s/../' % os.path.abspath(os.path.dirname(__file__)))
systemsDir = '%s/stratuslab/system' % modulePath
shareDir = '/var/share/stratuslab/'
etcDir = '/etc/stratuslab/'
defaultConfigFile = etcDir + 'stratuslab.cfg'
manifestExt = '.manifest.xml'
cliLineSplitChar = '#'

QUIET_VERBOSE_LEVEL = 0
NORMAL_VERBOSE_LEVEL = 1
DETAILED_VERBOSE_LEVEL = 2

# Environment variable names
envEndpoint = 'STRATUSLAB_ENDPOINT'

def wget(url, savePath):
    fd = urllib2.urlopen(url)
    filePutContent(savePath, fd.read())
    fd.close()
    
def ping(host, timeout=5, number=1, ** kwargs):
    '''Ping <host> and return True if successful'''
    #    p = subprocess.Popen(['ping', '-q', '-c', str(number), '-W', str(timeout), host], ** kwargs)
    p = subprocess.Popen(['ping', '-q', '-c', str(number), host], ** kwargs)
    p.wait()
    success = p.returncode == 0
    return success

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

def fileAppendContent(filename, data):
    fd = open(filename, 'a')
    fd.write(data)
    fd.close()
        
def shaHexDigest(string):
    shaMethod = None
    try:
        import hashlib
        shaMethod = hashlib.sha1
    except ImportError:
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
    hostUp = False
    while not hostUp:
        if ticks:
            sys.stdout.flush()
            sys.stdout.write('.')
        hostUp = ping(host, stdout=stdout, stderr=stderr)
        sleep(1)
        
        if time.time() - start > timeout:
            return False
        
    return hostUp

def sleep(seconds):
    time.sleep(seconds)

def setPythonPath(path):
    if not path in sys.path:
        sys.path.append(path)

def execute(cmd, **kwargs):
    wait = not kwargs.get('noWait', False)

    if kwargs.has_key('noWait'):
        del kwargs['noWait']
        
    verboseLevel = _extractVerboseLevel(kwargs)
    verboseThreshold = _extractVerboseThreshold(kwargs)
    
    printDetail('Calling: ' + ' '.join(cmd), verboseLevel, verboseThreshold)

    process = subprocess.Popen(cmd, **kwargs)

    if wait:
        process.wait()

    return process.returncode

def _extractVerboseLevel(kwargs):
    return _extractAndDeleteKey('verboseLevel', 0, kwargs)

def _extractVerboseThreshold(kwargs):
    return _extractAndDeleteKey('verboseThreshold', 2, kwargs)

def _extractAndDeleteKey(key, default, dict):
    value = default
    if key in dict:
        value = dict[key]
        del dict[key]
    return value

def printAction(msg):
    printAndFlush('\n :::%s:::\n' % (':' *len(msg)))
    printAndFlush(' :: %s ::\n' % msg)
    printAndFlush(' :::%s:::\n' % (':' *len(msg)))
    
def printStep(msg):
    printAndFlush('\n :: %s' % msg)

def printError(msg, exitCode=1, exit=True):
    printAndFlush('\n  [ERROR] %s\n' % msg)

    if exit:
        sys.exit(exitCode)

def printWarning(msg):
    printAndFlush('\n  [WARNING] %s\n' % msg)

def printAndFlush(msg):
    sys.stdout.flush()
    print msg,
    sys.stdout.flush()

def printDetail(msg,verboseLevel=1,verboseThreshold=1):
    if verboseLevel >= verboseThreshold:
        printAndFlush('\n    %s' % msg) 
    
def sshCmd(cmd, host, sshKey=None, port=22, user='root', timeout=5, **kwargs):
    sshCmd = ['ssh', '-p', str(port), '-o', 'ConnectTimeout=%s' % timeout, '-o', 'StrictHostKeyChecking=no']

    if sshKey and os.path.isfile(sshKey):
        sshCmd.append('-i')
        sshCmd.append(sshKey)

    sshCmd.append('%s@%s' % (user, host))
    sshCmd.append(cmd)

    return execute(sshCmd, **kwargs)

def scp(src, dest, sshKey=None, port=22, **kwargs):
    scpCmd = ['scp', '-P', str(port), '-r', '-o', 'StrictHostKeyChecking=no']

    if sshKey and os.path.isfile(sshKey):
        scpCmd.append('-i')
        scpCmd.append(sshKey)

    scpCmd.append(src)
    scpCmd.append(dest)
    
    return execute(scpCmd, **kwargs)

def importSystem(system):
    module = None
    try:
        module = __import__(system)
    except:
        msg = 'Error while importing module %s' % system
        printError('', exit=False)
        raise ImportException(msg)
    else:
        return module

def validateIp(ipAddress):
    return isValidIpV4(ipAddress) or isValidIpV6(ipAddress)

def isValidIpV4(ip):
    """Validates IPv4 addresses.
    """
    pattern = re.compile(r"""
        ^
        (?:
          # Dotted variants:
          (?:
            # Decimal 1-255 (no leading 0's)
            [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
          |
            0x0*[0-9a-f]{1,2}  # Hexadecimal 0x0 - 0xFF (possible leading 0's)
          |
            0+[1-3]?[0-7]{0,2} # Octal 0 - 0377 (possible leading 0's)
          )
          (?:                  # Repeat 0-3 times, separated by a dot
            \.
            (?:
              [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
            |
              0x0*[0-9a-f]{1,2}
            |
              0+[1-3]?[0-7]{0,2}
            )
          ){0,3}
        |
          0x0*[0-9a-f]{1,8}    # Hexadecimal notation, 0x0 - 0xffffffff
        |
          0+[0-3]?[0-7]{0,10}  # Octal notation, 0 - 037777777777
        |
          # Decimal notation, 1-4294967295:
          429496729[0-5]|42949672[0-8]\d|4294967[01]\d\d|429496[0-6]\d{3}|
          42949[0-5]\d{4}|4294[0-8]\d{5}|429[0-3]\d{6}|42[0-8]\d{7}|
          4[01]\d{8}|[1-3]\d{0,9}|[4-9]\d{0,8}
        )
        $
    """, re.VERBOSE | re.IGNORECASE)
    return pattern.match(ip) is not None

def isValidIpV6(ip):
    """Validates IPv6 addresses.
    """
    pattern = re.compile(r"""
        ^
        \s*                         # Leading whitespace
        (?!.*::.*::)                # Only a single whildcard allowed
        (?:(?!:)|:(?=:))            # Colon iff it would be part of a wildcard
        (?:                         # Repeat 6 times:
            [0-9a-f]{0,4}           #   A group of at most four hexadecimal digits
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
        ){6}                        #
        (?:                         # Either
            [0-9a-f]{0,4}           #   Another group
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
            [0-9a-f]{0,4}           #   Last group
            (?: (?<=::)             #   Colon iff preceeded by exacly one colon
             |  (?<!:)              #
             |  (?<=:) (?<!::) :    #
             )                      # OR
         |                          #   A v4 address with NO leading zeros
            (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            (?: \.
                (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            ){3}
        )
        \s*                         # Trailing whitespace
        $
    """, re.VERBOSE | re.IGNORECASE | re.DOTALL)
    return pattern.match(ip) is not None

def unifyNetsize(netsize):
    classes = { 'A': 2**24, 'B': 2**16, 'C': 2**8 }

    for letter, mask in classes.items():
        if netsize == letter:
            return mask
        
    return netsize

def networkSizeToNetmask(netsize):
    MAX_MASK_POW_TWO = 24
    MAX_MASK_LENTGH = 32
    for pow in range(MAX_MASK_POW_TWO):
        if 2**pow >= netsize:
            return MAX_MASK_LENTGH - pow
    return MAX_MASK_LENTGH

def assignAttributes(instance, dictionary):
    for key, value in dictionary.items():
        setattr(instance, key, value)

def randomString(length=10):
    return ''.join(sample(list(ascii_lowercase), length))

def runMethodByName(obj, methodName, *args, **kw):
    return obj.__class__.__dict__[methodName](obj, *args, **kw)

def generateSshKeyPair(keyFilename):
    try:
        os.remove(keyFilename)
        os.remove(keyFilename + '.pub')
    except(OSError):
        pass
    sshCmd = 'ssh-keygen -f %s -N "" -q' % keyFilename
    execute(sshCmd, shell=True)
