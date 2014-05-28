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
import os
import os.path
import re
import subprocess
import sys
import time
import urllib2
import random
import urlparse
import hashlib
from random import sample
from string import ascii_lowercase
import platform

from stratuslab.Exceptions import ExecutionException, ValidationException
import stratuslab.api.LogUtil as LogUtil

import Defaults

# TODO: Move to Defaults
utilPath = os.path.abspath(os.path.dirname(__file__))
defaultRepoConfigSection = 'stratuslab_repo'
defaultRepoConfigPath = '.stratuslab/stratuslab.repo.cfg'
modulePath = os.path.abspath(os.path.join(utilPath, os.pardir))
systemsDir = os.path.join(modulePath, 'stratuslab', 'system')
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
SSH_CONNECTION_RETRY_SLEEP_MAX = 60

UUID_REGEX = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
RE_UUID = re.compile(UUID_REGEX)


def get_share_file(path_elements, additional_path=None):
    '''
    Checks the list of possible share directories for a file with
    the given path elements.  If an additional path is given (which
    must be absolute and include the path elements already), then
    this path is checked first.  It returns the first file found or
    raises an exception if it doesn't exist.
    '''

    share_paths = [[Defaults.SHARE_DIR],
                   [utilPath, 'share'],
                   [modulePath, 'share'],
                   [modulePath, os.pardir, os.pardir, 'share'],
                   [modulePath, os.pardir, os.pardir, os.pardir, 'share'],
                   [modulePath, os.pardir, 'resources', 'share']]

    paths = []
    for share_path in share_paths:
        path = share_path + path_elements
        paths.append(os.path.join(*path))

    if additional_path:
        paths.insert(0, additional_path)

    for path in paths:
        if os.path.exists(path):
            return path

    raise Exception("could not locate file; tried:\n%s" % "\n".join(paths))


def get_template_file(path_elements, additional_path=None):
    elements = list(path_elements)
    elements.insert(0, 'template')
    return get_share_file(elements, additional_path)


def get_resources_file(path_elements, additional_path=None):
    elements = list(path_elements)
    elements.insert(0, 'template')
    return get_share_file(elements, additional_path)


def wget_as_xml(url, savePath):
    request = urllib2.Request(url, None, {'accept': 'application/xml'})
    fd = _wget(request)
    filePutContent(savePath, fd.read())
    fd.close()


def wget(url, savePath):
    fd = _wget(url)
    filePutContent(savePath, fd.read())
    fd.close()


def wstring_as_xml(url):
    request = urllib2.Request(url, None, {'accept': 'application/xml'})
    return wstring(request)


def wstring(url):
    fd = _wget(url)
    return fd.read()


def wread(url):
    return _wget(url)


def _wget(url):
    return urllib2.urlopen(url)


def ping(host, timeout=5, number=1, **kwargs):
    if systemName() == 'Darwin':
        timeout_opt = '-t'
    else:
        timeout_opt = '-w'
    p = subprocess.Popen(['ping', '-q', '-c', str(number),
                          timeout_opt, str(timeout), host], **kwargs)
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
    """
    A block in 'content' starts with the first line from 'data' or 'start'.
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
    for i, line in enumerate(lines):
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
    if insertIndex == len(lines) - 1:
        data += '\n'
    lines.insert(insertIndex, data)

    return '\n'.join(lines)


def fileGetContent(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content


def filePutContent(filename, data, neverShowData=True):
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


def fileFind(directory, start='', end=''):
    try:
        for f in os.listdir(directory):
            if f.startswith(start) and f.endswith(end):
                return os.path.join(directory, f)
    except OSError:
        pass

    raise ValueError("Can't find file starting with %s and ending with %s in directory %s" % (start, end, directory))


def shaHexDigest(string):
    h = hashlib.sha1(string)
    return h.hexdigest()


def waitUntilPingOrTimeout(host, timeout, ticks=True, stdout=None, stderr=None):
    if not stdout:
        stdout = open(os.path.devnull, 'w')
    if not stderr:
        stderr = open(os.path.devnull, 'w')

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

    if 'noWait' in kwargs:
        del kwargs['noWait']

    output = kwargs.get('withOutput', False)
    if output:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.STDOUT
        kwargs['close_fds'] = True
    if 'withOutput' in kwargs:
        del kwargs['withOutput']

    if isinstance(commandAndArgsList, list):
        _cmd = ' '.join(commandAndArgsList)
    else:
        _cmd = commandAndArgsList

    _printDetail('Calling: %s' % _cmd, kwargs)

    if isinstance(commandAndArgsList, list) and kwargs.get('shell', False) is True:
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


def _extractAndDeleteKey(key, default, dictionary):
    value = default
    if key in dictionary:
        value = dictionary[key]
        del dictionary[key]
    return value


def _format_action(msg):
    filler = ':' * (len(msg) + 6)
    fmt = '\n %s\n :: %s ::\n %s'
    return fmt % (filler, msg, filler)


def printAction(msg):
    LogUtil.info(_format_action(msg))


def printStep(msg):
    LogUtil.info(' :: %s' % msg)


def printInfo(msg):
    LogUtil.info(msg)


def printDebug(msg):
    LogUtil.debug(msg)


def printError(msg, exitCode=1, exit=True):
    # TODO: Revisit this design; having exit in API is not good.
    err = '  [ERROR] %s' % msg
    if exit:
        raise SystemExit(err)
    else:
        LogUtil.error(msg)


def printWarning(msg):
    LogUtil.warning('  [WARNING] %s' % msg)


def printDetail(msg, verboseLevel=1, verboseThreshold=1):
    # TODO: Review this to see if more levels are needed.
    if verboseThreshold == 0:
        LogUtil.info(msg)
    else:
        LogUtil.debug(msg)


def sshCmd(cmd, host, sshKey=None, port=22, user='root', timeout=5, passwordPrompts=0, **kwargs):
    def _appendToSshCommandFromKwargs(keyword, append):
        if kwargs.get(keyword, False):
            sshCmd.append(append)
        try:
            del kwargs[keyword]
        except:
            pass

    sshCmd = ['ssh',
              '-p', str(port),
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

    output = None
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
    try:
        return __import__(system)
    except ImportError, ex:
        msg = 'Error while importing module %s, with detail: ' % system
        printError(msg + str(ex), exit=False)
        raise


def loadModule(module_name):
    namespace = ''
    name = module_name
    if name.find('.') != -1:
        # There's a namespace so we take it into account
        namespace = '.'.join(name.split('.')[:-1])

    return __import__(name, fromlist=namespace)


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
    classes = {'A': 2 ** 24, 'B': 2 ** 16, 'C': 2 ** 8}

    for letter, mask in classes.items():
        if netsize == letter:
            return mask

    return netsize


def networkSizeToNetmask(netsize):
    MAX_MASK_POW_TWO = 24
    MAX_MASK_LENGTH = 32
    for exponent in range(MAX_MASK_POW_TWO):
        if 2 ** exponent >= netsize:
            return MAX_MASK_LENGTH - exponent
    return MAX_MASK_LENGTH


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
    except OSError:
        pass
    sshCmd = 'ssh-keygen -f %s -N "" -q' % keyFilename
    execute(sshCmd, shell=True)


def checkUrlExists(url, timeout=5):
    try:
        if not urllib2.urlopen(url, timeout=timeout):
            raise ExecutionException('urllib2.urlopen() did not return url handler.')
    except urllib2.URLError, ex:
        raise ValidationException(str(ex))
    return True


def constructEndPoint(fragment, protocol='https', port=8443, path=''):
    _protocol, _hostname, _port, _path = parseUri(fragment)

    _protocol = (_protocol and _protocol) or protocol + '://'
    _hostname = (_hostname and _hostname) or fragment
    _port = (_port and _port) or port
    _path = (_path and _path) or path

    return '%s%s:%s/%s' % (_protocol, _hostname, _port, _path)


def parseUri(uri):
    """Return tuple (protocol, hostname, port, path?query#fragment)"""
    m = re.match('([a-zA-Z0-9_]*://)?([^/:$]*):?(\d+)?/?(.*)', uri)
    protocol, hostname, port, path_and_query = m.group(1), m.group(2), m.group(3), m.group(4)
    return protocol, hostname, port, path_and_query


def sanitizeEndpoint(endpoint, protocol=Defaults.marketplaceProtocol, port=Defaults.marketplacePort):
    if not endpoint:
        return endpoint
    sanitized = endpoint
    _protocol, _, _, _ = parseUri(endpoint)
    if not _protocol:
        sanitized = constructEndPoint(sanitized, protocol, port)
    return sanitized.rstrip('/')  # trim all trailing slashes


def getHostnameFromUri(uri):
    return parseUri(uri)[1]


def getHostnamePortFromUri(uri):
    groups = parseUri(uri)
    port = (groups[2] and ':%s' % groups[2]) or ''
    return groups[1] + port


def getProtoFromUri(uri):
    return parseUri(uri)[0]


def getProtoHostnameFromUri(uri):
    return ''.join(parseUri(uri)[:2])


def getProtoHostnamePortFromUri(uri):
    groups = parseUri(uri)
    protoHost = ''.join(groups[:2])
    port = (groups[2] and ':%s' % groups[2]) or ''
    return protoHost + port


def getTimeInIso8601():
    """Return current time in iso8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time()))


def toTimeInIso8601(_time):
    """Convert int or float to time in iso8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_time))


def isTrueConfVal(var):
    return (str(var).lower() in ['true', 'yes', 'on', '1']) or False


def isFalseConfVal(var):
    return (str(var).lower() in ['false', 'no', 'off', '0', '']) or False


def escapeDoubleQuotes(string, times=1):
    return re.sub('"', '%s"' % ('\\' * times), string)


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
    """Assume that if no unit specified, already in KB"""
    unit = ('KB', 'MB', 'GB')
    try:
        valueKB = int(value)
    except ValueError:
        valueNum = value[:-2]
        valueUnit = (value[-2:]).strip().upper()
        valueKB = int(valueNum) * (1024 ** unit.index(valueUnit))
    return str(valueKB)


def is_uuid(str_uuid):
    return RE_UUID.match(str_uuid)


def importETree():
    try:
        import xml.etree.cElementTree as etree  # c-version first

        return etree
    except ImportError:
        try:
            import xml.etree.ElementTree as etree  # python version

            return etree
        except ImportError:
            raise Exception('failed to import ElementTree')


etree = importETree()


def etree_from_text(text):
    """
    The native fromstring method in etree doesn't handle unicode
    values correctly without explicit encoding in Python 2.x.  
    As the Python 2.x is essentially frozen, the python maintainers
    will not be fixing this in the distribution.
    """
    if isinstance(text, unicode):
        text = text.encode('utf-8')
    return etree.fromstring(text)
