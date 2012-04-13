import os
import tempfile
import subprocess
import datetime

from stratuslab import Defaults
from stratuslab import Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ExecutionException
from stratuslab.system import SystemFactory


class PortTranslation(object):
    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        self.configHolder.assign(self)

        self.system = SystemFactory.getSystem(self.frontendSystem, self.configHolder)
        self.runtime = datetime.datetime.now()

        self._setDefaultConfiguration()
        self._setFirewallConfiguration()
        self._setSudoConfiguration()
        self._setCloudConfiguration()

    def _getParametersName(self):
        return ['patPortsRange', 'patServiceHost', 'patServiceDbname',
                'patTranslatedPorts', 'patFirewallChainPrefix', 'patMaxTranslations',
                'patNetworks', 'patVerboseLevel']

    def _setDefaultConfiguration(self):
        for attr in self._getParametersName():
            default = getattr(Defaults, attr, None)
            if getattr(self, attr, None) is None:
                setattr(self, attr, default)

    def _setFirewallConfiguration(self):
        self.firewall = Firewall()
        self.firewallChains = {'nat' : ['PREROUTING'],
                               'filter': ['FORWARD']}

    def _setSudoConfiguration(self):
        self.sudoersFilePath = '/etc/sudoers'

    def _setCloudConfiguration(self):
        self.cloudUsername = self.oneUsername
        self.cloudConfigFilePath = '/etc/one/oned.conf'
        self.cloudHookDir = '/usr/share/one/hooks'
        self.cloudHookFilename = 'pathook.rb'
        self.cloudHookFilePath = os.path.join(self.cloudHookDir, self.cloudHookFilename)
        self.cloudHookTemplate = """
# %(hookid)s
VM_HOOK = [
    name      = "%(name)s",
    on        = "%(on)s",
    command   = "%(command)s",
    arguments = "%(arguments)s" ]
"""

    def _cleanConfiguration(self):
        try:
            self.patNetworks = self.patNetworks.split(',')
            self.patTranslatedPorts = map(int, self.patTranslatedPorts.split(','))
        except AttributeError:
            pass

        self.patMaxTranslations = int(self.patMaxTranslations)
        self.patVerboseLevel = int(self.patVerboseLevel)

    def _checkConfiguration(self):
        pass

    def _configureFirewall(self):
        self.firewall.backupConfig(self.firewall.permaFilePath + self.runtime.strftime('.%Y%m%d%H%M'))
        if self.patFirewallChainPrefix:
            try:
                self._createFirewallChains()
            except ExecutionException, error:
                self.firewall.restoreBackup()
                raise error
            finally:
                # NOTE: we assume that minimal iptables rules are set, i.e. no
                #       dynamic rules such as VM port translation.
                self.firewall.backupConfig(self.firewall.permaFilePath)

    def _createFirewallChains(self):
        for table, chains in self.firewallChains.iteritems():
            for chain in chains:
                name = '%s-%s' % (self.patFirewallChainPrefix, chain)
                if not self.firewall.isSetChain(table, name):
                    self.firewall.createChain(table, name)
                    self.firewall.insertRule(table, chain, name)

    def _configureSudo(self):
        Util.appendOrReplaceInFile(self.sudoersFilePath,
                'Defaults:%s !requiretty' % self.cloudUsername,
                'Defaults:%s !requiretty' % self.cloudUsername)
        Util.appendOrReplaceInFile(self.sudoersFilePath,
                '%s ALL= NOPASSWD: %s' % (self.cloudUsername, self.firewall.binary),
                '%s ALL= NOPASSWD: %s' % (self.cloudUsername, self.firewall.binary))

    def _configureCloud(self):
        self._addOrReplaceCloudHook()

    def _addOrReplaceCloudHook(self):
        data = self._buildAddPortTranslationHook()
        Util.appendOrReplaceMultilineBlockInFile(self.cloudConfigFilePath, data)

        data = self._buildDeletePortTranslationHook()
        Util.appendOrReplaceMultilineBlockInFile(self.cloudConfigFilePath, data)

    def _buildAddPortTranslationHook(self):
        args = "add '$VMID' -r '%s' -f '%s' -p '%s' -n '%s' -c '%s' -l '%s' -m '%s'" % (
                self.patPortsRange,
                self.patServiceDbname,
                ','.join(map(str, self.patTranslatedPorts)),
                ','.join(self.patNetworks),
                self.patFirewallChainPrefix,
                self.frontendIp,
                self.patMaxTranslations,
                )

        args = '%s %s' % (args, self._addHookVerboseMode())

        return self.cloudHookTemplate % {'hookid': 'AddPortTranslation hook',
                                         'name': 'AddPortTranslation',
                                         'on': 'RUNNING',
                                         'command': self.cloudHookFilePath,
                                         'arguments': args}

    def _buildDeletePortTranslationHook(self):
        args = "del '$VMID' -f '%s' -p '%s' -n '%s' -c '%s' -l '%s'" % (
                self.patServiceDbname,
                ','.join(map(str, self.patTranslatedPorts)),
                ','.join(self.patNetworks),
                self.patFirewallChainPrefix,
                self.frontendIp,
                )

        args = '%s %s' % (args, self._addHookVerboseMode())

        return self.cloudHookTemplate % {'hookid': 'DelPortTranslation hook',
                                         'name': 'DelPortTranslation',
                                         'on': 'DONE',
                                         'command': self.cloudHookFilePath,
                                         'arguments': args}

    def _addHookVerboseMode(self):
        if self.patVerboseLevel > Util.NORMAL_VERBOSE_LEVEL:
            return '-%s' % ('v' * self.patVerboseLevel)
        return ''

    def run(self):
        self._cleanConfiguration()
        self._checkConfiguration()

        Util.printStep('configure firewall')
        self._configureFirewall()

        Util.printStep('configure sudo')
        self._configureSudo()

        Util.printStep('configure cloud')
        self._configureCloud()

        Util.printStep('restart cloud system')
        self.system.startCloudSystem()

class Firewall(object):
    """
    FIXME: merge with what the BaseSystem class provides.
    """

    def __init__(self):
        self.binary = '/sbin/iptables'
        self.saveBinary = '/sbin/iptables-save'
        self.restoreBinary = '/sbin/iptables-restore'
        self.permaFilePath = '/etc/sysconfig/iptables'

    def backupConfig(self, filename=None):
        if not filename:
            handler, self.backupFile = tempfile.mkstemp()
        else:
            self.backupFile = filename
            handler = open(self.backupFile, 'w+')

        p = subprocess.Popen([self.saveBinary], stdout=handler)
        p.wait()
        if p.returncode:
            raise RuntimeException
        handler.close()

    def restoreBackup(self):
        handler = open(self.backupFile, 'r')
        subprocess.Popen([self.restoreBinary], stdin=handler)
        handler.close()

    def destroyBackup(self):
        if os.path.exists(self.backupFile):
            os.remove(self.backupFile)

    def createChain(self, table, chain):
        cmd = '%s -t %s -N %s' % (self.binary, table, chain)
        self._execute(cmd)

    def insertRule(self, table, chain, action, condition=None, position=1):
        cmd = '%s -t %s -I %s %s -j %s' % (self.binary, table, chain, position, action)
        if condition:
            cmd = '%s %s' % (cmd, condition)
        self._execute(cmd)

    def appendRule(self, table, chain, action, condition=None):
        cmd = '%s -t %s -A %s -j %s' % (self.binary, table, chain, action)
        if condition:
            cmd = '%s %s' % (cmd, condition)
        self._execute(cmd)

    def _execute(self, cmd):
        Util.executeRaiseOnError(cmd)

    def getChains(self):
        p = subprocess.Popen([self.saveBinary], stdout=subprocess.PIPE)
        output = p.communicate()[0]
        if p.returncode:
            raise RuntimeException

        chains = {}
        table = None
        for line in output.split('\n'):
            if line.startswith('*'):
                table = line[1:].strip()
                chains[table] = []
            elif line.startswith(':'):
                chains[table] = line[1:].split()[0]

        return chains

    def isSetChain(self, table, chain):
        chains = self.getChains()
        if not chains.has_key(table):
            return False
        return (chain in chains[table])

