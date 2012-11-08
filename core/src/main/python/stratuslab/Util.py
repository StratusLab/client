#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
import codecs
import os.path
import re
import subprocess
import sys
import time
import urllib2
import random
import urlparse
import hashlib
import gzip
import io
from random import sample
from string import ascii_lowercase
from stratuslab.Exceptions import ExecutionException, ValidationException
import Defaults
import platform

# TODO: Move to Defaults
defaultRepoConfigSection = 'stratuslab_repo'
defaultRepoConfigPath = '.stratuslab/stratuslab.repo.cfg'
modulePath = os.path.abspath('%s/../' % os.path.abspath(os.path.dirname(__file__)))
systemsDir = '%s/stratuslab/system' % modulePath
varLibDir = '/var/lib/stratuslab/python'
defaultConfigFile = os.path.join(Defaults.ETC_DIR, 'stratuslab.cfg')
defaultConfigFileUser = os.path.join(Defaults.userHome, '.stratuslab', 'stratuslab-user.cfg')
manifestExt = '.xml'
cliLineSplitChar = '#'

VERBOSE_LEVEL_QUIET = 0
VERBOSE_LEVEL_NORMAL = 1
VERBOSE_LEVEL_DETAILED = 2

# Environment variable names
envEndpoint = 'STRATUSLAB_ENDPOINT'
userConfigFileSelectedSection = 'STRATUSLAB_USER_CONFIG_SECTION'

SSH_EXIT_STATUS_ERROR = 255
SSH_CONNECTION_RETRY_NUMBER = 2
SSH_CONNECTION_RETRY_SLEEP_MAX = 5

def getShareDir():
    if os.path.exists(Defaults.SHARE_DIR):
        return Defaults.SHARE_DIR
    else:
        return os.path.join(os.path.dirname(__file__),'../../../../share')

def getTemplateDir():
    if os.path.exists(Defaults.TEMPLATE_DIR):
        return Defaults.TEMPLATE_DIR
    else:
        return os.path.join(os.path.dirname(__file__),'../../../../share/template')

def getResourcesDir():
    if os.path.exists(Defaults.RESOURCES_DIR):
        return Defaults.RESOURCES_DIR
    else:
        return os.path.join(os.path.dirname(__file__),'../../../../share/resources')

def wget(url, savePath):
    fd = _wget(url)
    filePutContent(savePath, fd.read())
    fd.close()

def wstring(url):
    fd = _wget(url)
    return fd.read()

def wread(url):
    return _wget(url)

def _wget(url):
    return urllib2.urlopen(url)

def ping(host, timeout=5, number=1, ** kwargs):
    if systemName() == 'Darwin':
        timeout_opt = '-t'
    else:
        timeout_opt = '-w'
    p = subprocess.Popen(['ping', '-q', '-c', str(number), 
                                timeout_opt, str(timeout), host], ** kwargs)
    p.wait()
    success = (p.returncode == 0)
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

def appendOrReplaceMultilineBlockInFile(filename, data, start='', until=''):
    content = fileGetContent(filename)
    newContent = appendOrReplaceMultilineBlockInString(content, data, 
                                                       start=start, until=until)
    filePutContent(filename, newContent)

def appendOrReplaceMultilineBlockInString(content, data, start='', until=''):
    """A block in 'content' starts with the first line from 'data' or 'start'. 
    Block ends right before 'until'.
    """
    if not until:
        until = '([ ]*|[ ]*#.*)$'
    
    if not start:
        data = data.strip()
        beginStr = data.split('\n', 1)[0]

        if not re.search(beginStr, content, re.M):
            return '%s%s%s\n\n' % (content, content.endswith('\n') and '\n' or '\n\n',
                                   data)
    else:
        beginStr = start

        beginStr_in_content = False
        for line in content.split('\n'):
            if line.startswith(beginStr):
                beginStr_in_content = True
                break

        if not beginStr_in_content:
            return '%s%s%s\n\n' % (content, content.endswith('\n') and '\n' or '\n\n',
                                   data)

    lines = content.split('\n')

    lineNums = []
    for i,line in enumerate(lines):
        if line.startswith(beginStr):
            lineNums.append(i)
            break

    insertIndex = lineNums[0]
    k = lineNums[0] + 1
    try:
        search_until = re.compile(until)
        while not search_until.match(lines[k]):
            lineNums.append(k)
            k += 1
    except IndexError:
        pass
    lineNums.reverse()
    for n in lineNums:
        del lines[n]
    if insertIndex == len(lines)-1:
        data = data + '\n'
    lines.insert(insertIndex, data)

    return '\n'.join(lines)

def fileGetContent(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content

def filePutContent(filename, data, neverShowData=False):
    _printDetail('Creating file %s with content: \n%s\n' % (filename, 
                                (neverShowData and '<hidden>' or data)))
    if isinstance(data, unicode):
        fh = codecs.open(filename, 'w', 'utf8')
    else:
        fh = open(filename, 'wb')
    fh.write(data)
    fh.close()

def fileAppendContent(filename, data):
    fd = open(filename, 'a')
    fd.write(data)
    fd.close()

def fileGetExtension(filename):
    try:
        ending = filename.rsplit('.', 1)[1]
    except IndexError:
        return ''
    if not ending:
        return ''
    return ending

def fileFind(dir, start='', end=''):
    try:
        for file in os.listdir(dir):
            if file.startswith(start) and file.endswith(end):
                return os.path.join(dir, file)
    except OSError:
        pass

    raise ValueError("Can't find file starting with %s and ending with %s in directory %s" % (start, end, dir))

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
            if ticks:
                sys.stdout.flush()
                sys.stdout.write('\n')
            return False

    if ticks:
        sys.stdout.flush()
        sys.stdout.write('\n')
    return hostUp

def sleep(seconds):
    time.sleep(seconds)

def setPythonPath(path):
    if not path in sys.path:
        sys.path.append(path)

def execute(commandAndArgsList, **kwargs):
    wait = not kwargs.get('noWait', False)

    if kwargs.has_key('noWait'):
        del kwargs['noWait']

    output = kwargs.get('withOutput', False)
    if output:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.STDOUT
        kwargs['close_fds'] = True
    if kwargs.has_key('withOutput'):
        del kwargs['withOutput']

    if isinstance(commandAndArgsList, list):
        _cmd = ' '.join(commandAndArgsList)
    else:
        _cmd = commandAndArgsList

    _printDetail('Calling: %s' % _cmd, kwargs)

    if isinstance(commandAndArgsList, list) and kwargs.get('shell', False) == True:
        commandAndArgsList = ' '.join(commandAndArgsList)

    process = subprocess.Popen(commandAndArgsList, **kwargs)

    if wait:
        process.wait()

    if output:
        return process.returncode, process.stdout.read()
    else:
        return process.returncode

def executeGetStatusOutput(commandAndArgsList, **kwargs):
    kwargs['withOutput'] = True
    return execute(commandAndArgsList, **kwargs)

def executeRaiseOnError(cmd):
    res, output = execute(cmd.split(' '), withOutput=True)
    if res:
        raise ExecutionException('Failed executing %s with detail %s' % (cmd, output))

def _printDetail(message, kwargs={}):
    verboseLevel = _extractVerboseLevel(kwargs)
    verboseThreshold = _extractVerboseThreshold(kwargs)
    printDetail(message, verboseLevel, verboseThreshold)

def _extractVerboseLevel(kwargs):
    return _extractAndDeleteKey('verboseLevel', VERBOSE_LEVEL_QUIET, kwargs)

def _extractVerboseThreshold(kwargs):
    return _extractAndDeleteKey('verboseThreshold', VERBOSE_LEVEL_DETAILED, kwargs)

def _extractAndDeleteKey(key, default, dict):
    value = default
    if key in dict:
        value = dict[key]
        del dict[key]
    return value

def printAction(msg):
    printAndFlush('\n :::%s:::\n' % (':' * len(msg)))
    printAndFlush(' :: %s ::\n' % msg)
    printAndFlush(' :::%s:::\n' % (':' * len(msg)))

def printStep(msg):
    printAndFlush(' :: %s\n' % msg)

def printError(msg, exitCode=1, exit=True):
    err = '  [ERROR] %s\n' % msg
    if exit:
        raise SystemExit(err)
    else:
        printAndFlush(msg)

def printWarning(msg):
    printAndFlush('  [WARNING] %s\n' % msg)

def printAndFlush(msg):
    sys.stdout.flush()
    print msg,
    sys.stdout.flush()

def printDetail(msg, verboseLevel=1, verboseThreshold=1):
    if verboseLevel >= verboseThreshold:
        _msg = (msg.endswith('\n') and msg) or msg + '\n'
        printAndFlush('    %s' % _msg)

def sshCmd(cmd, host, sshKey=None, port=22, user='root', timeout=5, passwordPrompts=0, **kwargs):
    
    def _appendToSshCommandFromKwargs(keyword, append):
        if kwargs.get(keyword, False):
            sshCmd.append(append)
        try:
            del kwargs[keyword]
        except: pass

    sshCmd = ['ssh', '-p', str(port),
              '-o', 'ConnectTimeout=%s' % timeout,
              '-o', 'StrictHostKeyChecking=no']
    sshCmd.append('-o NumberOfPasswordPrompts=%d' % int(passwordPrompts))

    if sshKey and os.path.isfile(sshKey):
        sshCmd.append('-i')
        sshCmd.append(sshKey)

    for keyAppend in [('sshVerb', '-v'), ('sshQuiet', '-q'), ('pseudoTTY', '-t')]:
        _appendToSshCommandFromKwargs(*keyAppend)

    sshCmd.append('%s@%s' % (user, host))
    sshCmd.append(cmd)

    for i in range(0, SSH_CONNECTION_RETRY_NUMBER + 1):
        if i > 0:
            sleepTime = random.randint(0, SSH_CONNECTION_RETRY_SLEEP_MAX)
            _printDetail('[%i] Retrying ssh command in %i sec.' % (i, sleepTime), kwargs.copy())
            time.sleep(sleepTime)
        output = execute(sshCmd, **kwargs)
        if isinstance(output, int):
            es = output
        else:
            es = output[0]
        if es != SSH_EXIT_STATUS_ERROR:
            return output
    return output

def sshCmdWithOutput(cmd, host, sshKey=None, port=22, user='root', timeout=5, **kwargs):
    return sshCmd(cmd, host, sshKey=sshKey, port=port,
                  user=user, timeout=timeout, withOutput=True, **kwargs)

def sshCmdWithOutputVerb(cmd, host, sshKey=None, port=22, user='root', timeout=5, **kwargs):
    return sshCmd(cmd, host, sshKey=sshKey, port=port,
                  user=user, timeout=timeout, withOutput=True, sshVerb=True, **kwargs)

def sshCmdWithOutputQuiet(cmd, host, sshKey=None, port=22, user='root', timeout=5, **kwargs):
    return sshCmd(cmd, host, sshKey=sshKey, port=port,
                  user=user, timeout=timeout, withOutput=True, sshQuiet=True, **kwargs)

def sshInteractive(host, sshKey=None, port=22, user='root', timeout=5, passwordPrompts=3, **kwargs):
    return sshCmd('', host, sshKey=sshKey, port=port, user=user,
            timeout=timeout, passwordPrompts=passwordPrompts, **kwargs)

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
    except ImportError, ex:
        msg = 'Error while importing module %s, with detail: ' % system
        printError(msg + str(ex), exit=False)
        raise
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

def gatewayIpFromNetAddress(network):
    net, start = network.rsplit('.', 1)
    return '%s.%i' % (net, int(start) + 1)

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

def checkUrlExists(url, timeout=5):
    fh = None
    try:
        fh = urllib2.urlopen(url, timeout=timeout)
    except urllib2.URLError, ex:
        raise ValidationException(str(ex))
    else:
        if not fh:
            raise ExecutionException('urllib2.urlopen() did not return url handler.')
    return True

def printEmphasisStart():
    sys.stdout.write('\033[1;31m')

def printEmphasisStop():
    sys.stdout.write('\033[0m')

def constructEndPoint(fragment, protocol='https', port=8443, path=''):

    _protocol, _hostname, _port, _path = parseUri(fragment)

    _protocol = (_protocol and _protocol) or protocol + '://'
    _hostname = (_hostname and _hostname) or fragment
    _port = (_port and _port) or port
    _path = (_path and _path) or path

    return '%s%s:%s/%s' % (_protocol, _hostname, _port, _path)

def parseUri(uri):
    '''Return tuple (protocol, hostname, port, path?query#fragment)'''
    m = re.match('([a-zA-Z0-9_]*://)?([^/:$]*):?(\d+)?/?(.*)', uri)
    protocol, hostname, port, path_and_query = m.group(1), m.group(2), m.group(3), m.group(4)
    return protocol, hostname, port, path_and_query

def sanitizeEndpoint(endpoint, protocol=Defaults.marketplaceProtocol, port=Defaults.marketplacePort):
    if not endpoint:
        return endpoint
    sanitized = endpoint
    _protocol, _, _, _ = parseUri(endpoint)
    if not _protocol:
        sanitized = constructEndPoint(sanitized, protocol, port)[:-1] # trim trailing /
    return sanitized

def getHostnameFromUri(uri):
    return parseUri(uri)[1]

def getProtoFromUri(uri):
    return parseUri(uri)[0]

def getProtoHostnameFromUri(uri):
    return ''.join(parseUri(uri)[:2])

def getProtoHostnamePortFromUri(uri):
    groups = parseUri(uri)
    protoHost = ''.join(groups[:2])
    port = (groups[2] and ':%s'%groups[2]) or ''
    return protoHost + port

def getTimeInIso8601():
    "Return current time in iso8601 format."
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))

def toTimeInIso8601(_time):
    "Convert int or float to time in iso8601 format."
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_time))

def isTrueConfVal(var):
    return (str(var).lower() in ['true', 'yes', 'on', '1']) or False

def isFalseConfVal(var):
    return (str(var).lower() in ['false', 'no', 'off', '0', '']) or False

def importETree():
    try:
        from lxml import etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.cElementTree as etree
        except ImportError:
            try:
                # Python 2.5
                import xml.etree.ElementTree as etree
            except ImportError:
                try:
                    # normal cElementTree install
                    import cElementTree as etree
                except ImportError:
                    try:
                        # normal ElementTree install
                        import elementtree.ElementTree as etree
                    except ImportError:
                        raise Exception("Failed to import ElementTree from any known place")

    if not hasattr(etree, '_fromstring'):
        etree._fromstring = etree.fromstring

        def fromstring(text):
            if isinstance(text, unicode):
                return etree._fromstring(text.encode('utf-8'))
            return etree._fromstring(text)

        etree.fromstring = fromstring
    
    return etree

def escapeDoubleQuotes(string, times=1):
    return re.sub('"', '%s"' % ('\\'*times), string)

def sanitizePath(path):
    subs = [('\ ', ' ')]
    for s in subs:
        path = path.replace(*s)
    return path

def isValidNetLocation(url):
    r = urlparse.urlsplit(url)
    return (r.scheme and r.netloc) and True or False

def systemName():
    return platform.system()

def compressionFromFilename(filename):
    """Will check the filename to see if it ends with a gzip or bzip2
       suffix, ignoring case.  If so, it returns 'gz' or 'bz2',
       respectively.  It returns the empty string otherwise. """
    lc_filename = filename.lower()
    if (lc_filename.endswith('.gz')):
        return 'gz'
    elif (lc_filename.endswith('.bz2')):
        return 'bz2'
    else:
        return ''

def openCompressedFile(filename, options='rb'):
    """Returns an open file handle for the given filename.  If the
       filename ends with a gzip or bzip2 suffix, then the file is
       opened as a gzip or bzip2 file."""
    type = compressionFromFilename(filename)
    if (type == 'gz'):
        return gzip.open(filename, options)
    elif (type == 'bz2'):
        return bz2.BZ2File(filename, options)
    else:
        return open(filename, options)

def _checksum_f(f, checksums=[], chunk_size=1024*1024*10):
    """Return a dictionary of checksums for the given file handle.  The
       file named by the file handle will be fully read if checksums
       are requested.  This method will close the file handle."""

    with f: 

        if not checksums:
            return {}

        digesters = []
        try:
            digesters = map(hashlib.new, checksums)
        except ValueError as e:
            raise ExecutionException('%s' % e)

        for chunk in iter((lambda:f.read(chunk_size)),''):
            for digester in digesters:
                digester.update(chunk)

        digests = [d.hexdigest() for d in digesters]

        return dict(zip(checksums, digests))

def checksum_file(filename, checksums=[], chunk_size=1024*1024*10):
    """Return dictionary of checksums."""

    return _checksum_f(open(filename, 'rb'), checksums, chunk_size)

def incrementMinorVersionNumber(version_string):
    vsplit = version_string.split('.')
    vsplit[1] = str(int(vsplit[1]) + 1)
    return '.'.join(vsplit)

def service(name, action):
    printDetail('Trying to %s %s' % (action, name))
    execute(['/etc/init.d/%s' % name, action])
    
def startService(name):
    service(name, 'start')

def stopService(name):
    service(name, 'stop')

def restartService(name):
    service(name, 'restart')
    
def getValueInKB(value):
    ''' Assume that if no unit specified, already in KB 
    '''
    unit = ('KB', 'MB', 'GB')
    try:
        valueKB = int(value)
    except ValueError:
        valueNum = value[:-2]
        valueUnit = (value[-2:]).strip().upper()
        valueKB = int(valueNum) * (1024 ** unit.index(valueUnit))
    return str(valueKB)
