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
import re
import os
import shutil
from datetime import datetime
import time

from stratuslab.Util import appendOrReplaceInFile
from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import execute
from stratuslab.Util import fileAppendContent
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
import stratuslab.Util as Util
from stratuslab.Util import printDetail
from stratuslab.Util import gatewayIpFromNetAddress
from stratuslab.Exceptions import ExecutionException

class BaseSystem(object):
    
    def __init__(self):
        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')
        self.workOnFrontend()

    def init(self):
        self._setOneHome()

    # -------------------------------------------
    #     Packages manager and related
    # -------------------------------------------
    
    def updatePackageManager(self):
        pass

    def installWebServer(self):
        pass

    def installPackages(self, packages):
        pass

    def installNodePackages(self, packages):
        if len(packages) > 0:
            if self._nodeShell('%s %s' %
                (self.installCmd, ' '.join(packages))):
                raise ExecutionException('Error installing packages: %s' % packages)

    def installFrontendDependencies(self):
        self.updatePackageManager()
        self.installPackages(self.frontendDeps)

    def installNodeDependencies(self):
        self.installNodePackages(self.nodeDeps)

    def installHypervisor(self):
        self.installNodePackages(self.hypervisorDeps.get(self.hypervisor))

    def startCloudSystem(self):
        try:
            self._cloudAdminExecute(['one stop'])
        except ExecutionException:
            pass
        self._cloudAdminExecute(['one start'])
        printDetail('Waiting for ONE to finish starting')
        time.sleep(10)

    # -------------------------------------------
    #     ONE admin creation
    # -------------------------------------------

    def createCloudGroup(self, groupname, gid):
        self.oneGroup = groupname
        self.oneGid = gid

        self.executeCmd(['groupadd', '-g', self.oneGid, 
                        self.oneGroup])

    def createCloudAdmin(self):

        self.createDirsCmd(os.path.dirname(self.oneHome))
        self.executeCmd(['useradd', '-d', self.oneHome, '-g', 
                        self.oneGroup, '-u', self.oneUid, self.oneUsername,
                        '-s', '/bin/bash', '-p', self.onePassword, '--create-home'])

    # -------------------------------------------
    #     ONE admin env config and related
    # -------------------------------------------

    def configureCloudAdminEnv(self, ONeDPort, stratuslabLocation):
        self.ONeDPort = ONeDPort

        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                      'export ONE_LOCATION',
                                      'export ONE_LOCATION=%s' % self.oneHome)
        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome, 
                                      'export ONE_XMLRPC',
                                      'export ONE_XMLRPC=http://localhost:%s/RPC2' % self.ONeDPort)
        self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                      'export PATH',
                                      'export PATH=%s/bin:%s' % (self.oneHome, os.getenv('PATH')))

        if stratuslabLocation:
            self.appendOrReplaceInFileCmd('%s/.bashrc' % self.oneHome,
                                          'export STRATUSLAB_LOCATION',
                                          'export STRATUSLAB_LOCATION=%s' % stratuslabLocation)

        self.filePutContentsCmd('%s/.bash_login' % self.oneHome,
                                '[ -f ~/.bashrc ] && source ~/.bashrc')
        self.setOwnerCmd('%s/.bash_login' % self.oneHome)

        # Hack to always load .bashrc
        self.executeCmd(['sed -i \'s/\[ -z \\\"\$PS1\\\" \\] \\&\\& ' 
                        'return/#&/\' %s/.bashrc' % self.oneHome], shell=True)

    def configureCloudAdminSshKeys(self):  
        keyFileName = '%s/.ssh/id_rsa' % self.oneHome

        if os.path.exists(keyFileName):
            printDetail('Key file %s already exists, skipping this step' % keyFileName)
            return

        self.createDirsCmd(os.path.dirname(keyFileName))
        self.setOwnerCmd(os.path.dirname(keyFileName))
        self.executeCmd(['ssh-keygen -f %s -N "" -q' % keyFileName],
                        shell=True)
        self.setOwnerCmd(keyFileName)
        self.setOwnerCmd('%s.pub' % keyFileName)

        self.copyCmd('%s.pub' % keyFileName, 
                     '%s/.ssh/authorized_keys' % self.oneHome)
        self.setOwnerCmd('%s/.ssh/authorized_keys' % self.oneHome)
        self._configureCloudAdminSsh()

    def configureCloudAdminSshKeysNode(self):
        self.createDirsCmd('%s/.ssh/' % self.oneHome)
        self.setOwnerCmd('%s/.ssh/' % self.oneHome)
        
        oneKey = fileGetContent('%s/.ssh/id_rsa' % self.oneHome)
        self._filePutContentAsOneAdmin('%s/.ssh/id_rsa' % self.oneHome, oneKey)
        
        oneKeyPub = fileGetContent('%s/.ssh/id_rsa.pub' % self.oneHome)
        self._filePutContentAsOneAdmin('%s/.ssh/authorized_keys' % self.oneHome,
                                       oneKeyPub)
        self.chmodCmd('%s/.ssh/id_rsa' % self.oneHome, 0600)
        self._configureCloudAdminSsh()

    def _configureCloudAdminSsh(self):
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.oneHome, 
                                      'Host', 'Host *')
        self.appendOrReplaceInFileCmd('%s/.ssh/config' % self.oneHome, 
                                      '\tStrictHost', '\tStrictHostKeyChecking no')

    def configureCloudAdminAccount(self):
        oneAuthFile = '%s/.one/one_auth' % self.oneHome
        self.appendOrReplaceInFileCmd(oneAuthFile, 
                                      self.oneUsername, '%s:%s' % (self.oneUsername, self.onePassword))

    def _setOneHome(self):
        if not self.oneHome:
            self.oneHome = os.path.expanduser('~' + self.oneUsername)

    # -------------------------------------------
    #     File sharing configuration
    # -------------------------------------------

    def configureNewNfsServer(self, mountPoint, networkAddr, networkMask):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/exports', 
                                      mountPoint, '%s %s/%s(rw,async,no_subtree_check,no_root_squash)' %
                                      (mountPoint, networkAddr, networkMask))
        self.executeCmd(['exportfs', '-a'])

    def configureExistingNfsShare(self, shareLocation, mountPoint):
        self.createDirsCmd(mountPoint)
        self.appendOrReplaceInFileCmd('/etc/fstab', shareLocation,
                                      '%s %s nfs soft,intr,rsize=32768,wsize=32768,rw 0 0' % (
                                      shareLocation, mountPoint))
        self.executeCmd(['mount', '-a'])
        
    def configureSshServer(self):
        pass

    def configureSshClient(self, sharedDir):
        self.createDirsCmd(sharedDir)
        self.setOwnerCmd(sharedDir)

    # -------------------------------------------
    #     Hypervisor configuration
    # -------------------------------------------

    def configureHypervisor(self):
        if self.hypervisor == 'xen':
            self._configureXen()
        elif self.hypervisor == 'kvm':
            self._configureKvm()

    def _configureKvm(self):
        self.executeCmd(['modprobe', 'kvm_intel'])
        self.executeCmd(['modprobe', 'kvm_amd'])

    def _configureXen(self):
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.oneUsername,
                                      '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xm *' % self.oneUsername)
        self.appendOrReplaceInFileCmd('/etc/sudoers', self.oneUsername,
                                      '%s  ALL=(ALL) NOPASSWD: /usr/sbin/xentop *' % self.oneUsername)
        self.executeCmd(['sed -i -E \'s/Defaults[[:space:]]+requiretty/#&/\''
                        ' /etc/sudoers'])

    # -------------------------------------------
    #     Front-end related methods
    # -------------------------------------------

    def execute(self, command):
        return self._execute(command)

    def _execute(self, command, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        return execute(command, 
                       stdout=stdout, 
                       stderr=stderr, 
                       verboseLevel=self.verboseLevel, 
                       verboseThreshold=Util.DETAILED_VERBOSE_LEVEL, 
                       **kwargs)

    def _executeWithOutput(self, command, **kwargs):
        kwargs['withOutput'] = True
        return self._execute(command, **kwargs)
    
    def _cloudAdminExecute(self, command, **kwargs):
        su = ['su', '-l', self.oneUsername, '-c']
        su.extend(command)
        res = self._execute(su, **kwargs)
        if res:
            raise ExecutionException('error executing command %s, with code: %s' % (command, res))            
    
    def _setCloudAdminOwner(self, path):
        os.chown(path, int(self.oneUid), int(self.oneGid)) 
        
    def _createDirs(self, path):
        if not os.path.isdir(path) and not os.path.isfile(path):
            os.makedirs(path)

    def _copy(self, src, dst):
        if os.path.isfile(src):
            shutil.copy(src, dst)
        else:
            shutil.copytree(src, dst)

    def _remove(self, path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)

    # -------------------------------------------
    #     Node related methods
    # -------------------------------------------

    def _nodeShell(self, command, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        if type(command) == type(list()):
            command = ' '.join(command)

        return sshCmd(command, 
                      self.nodeAddr, 
                      self.nodePrivateKey,
                      stdout=stdout, 
                      stderr=stderr,
                      verboseLevel=self.verboseLevel,
                      verboseThreshold=Util.DETAILED_VERBOSE_LEVEL, 
                      **kwargs)

    def _nodeCopy(self, source, dest, **kwargs):
        stdout = kwargs.get('stdout', self.stdout)
        stderr = kwargs.get('stderr', self.stderr)

        if kwargs.has_key('stdout'):
            del kwargs['stdout']
        if kwargs.has_key('stderr'):
            del kwargs['stderr']

        return scp(source, 
                   'root@%s:%s' % (self.nodeAddr, dest),
                   self.nodePrivateKey,
                   stdout=stdout,
                   stderr=stderr,
                   verboseLevel=self.verboseLevel,
                   verboseThreshold=Util.DETAILED_VERBOSE_LEVEL, 
                   **kwargs)

    def _remoteSetCloudAdminOwner(self, path):
        self._nodeShell(['chown %s:%s %s' % (self.oneUid, 
                        self.oneGid, path)])
            
    def _remoteCreateDirs(self, path):
        self._nodeShell('mkdir -p %s' % path)
        
    def _remoteAppendOrReplaceInFile(self, filename, search, replace):
        res = self._nodeShell(['grep', search, filename])

        if self._patternExists(res):
            self._nodeShell(['sed -i \'s#%s.*#%s#\' %s' % (
                            search, replace, filename)], shell=True)
        else:
            self._remoteFileAppendContents(filename, replace)

    def _patternExists(self, returnCode):
        return returnCode == 0
    
    def _remoteCopyFile(self, src, dest):
        self._nodeShell(['cp -rf %s %s' % (src, dest)])

    def _remoteRemove(self, path):
        self._nodeShell(['rm -rf %s' % path])
        
    def _remoteFilePutContents(self, filename, data):
        self._nodeShell('echo \'%s\' > %s' % (data, filename))

    def _remoteFileAppendContents(self, filename, data):
        self._nodeShell('echo \'%s\' >> %s' % (data, filename))
        
    def _filePutContentAsOneAdmin(self, filename, content):
        self.filePutContentsCmd(filename, content)
        self.setOwnerCmd(filename)

    def _remoteChmod(self, path, mode):
        return self._nodeShell('chmod %o %s' % (mode, path))
        
    # -------------------------------------------
    #     General
    # -------------------------------------------
    
    def setNodeAddr(self, nodeAddr):
        self.nodeAddr = nodeAddr

    def setNodePort(self, nodePort):
        self.nodePort = nodePort

    def setNodePrivateKey(self, privateKey):
        self.nodePrivateKey = privateKey

    def setNodeHypervisor(self, hypervisor):
        self.hypervisor = hypervisor

    def setCloudAdminName(self, username):
        self.oneUsername = username

    def workOnFrontend(self):
        self.appendOrReplaceInFileCmd = appendOrReplaceInFile
        self.setOwnerCmd = self._setCloudAdminOwner
        self.executeCmd = self._execute
        self.executeCmdWithOutput = self._executeWithOutput
        self.createDirsCmd = self._createDirs
        self.filePutContentsCmd = filePutContent
        self.fileAppendContentsCmd = fileAppendContent
        self.chmodCmd = os.chmod
        self.copyCmd = self._copy
        self.duplicateCmd = self._copy
        self.removeCmd = self._remove
        
    def workOnNode(self):
        self.appendOrReplaceInFileCmd = self._remoteAppendOrReplaceInFile
        self.setOwnerCmd = self._remoteSetCloudAdminOwner
        self.executeCmd = self._nodeShell
        self.duplicateCmd = self._remoteCopyFile
        self.createDirsCmd = self._remoteCreateDirs
        self.filePutContentsCmd = self._remoteFilePutContents
        self.fileAppendContentsCmd = self._remoteFileAppendContents
        self.chmodCmd = self._remoteChmod
        self.copyCmd = self._nodeCopy
        self.removeCmd = self._remoteRemove

    def configureCloudProxyService(self):
        self.installPackages(['stratuslab-cloud-proxy'])        
        self._configureProxyDefaultUsers()
        self._restartJetty()
        
    def _configureProxyDefaultUsers(self):
        self._configureProxyDefaultUsersUsernamePassword()

    def _configureProxyDefaultUsersUsernamePassword(self):
        filename = '/opt/jetty-7/etc/login/login-pswd.properties'
        search = self.oneUsername
        replace = '%(oneUsername)s=%(proxyOneadminPassword)s,cloud-access' % self.__dict__
        Util.appendOrReplaceInFile(filename, search, replace)

    def _restartJetty(self):
        self.executeCmd('/etc/init.d/jetty restart'.split(' '))

    # -------------------------------------------
    # Firewall
    # -------------------------------------------

    # TODO: extract Firewall class from the code below

    DEFAULT_FIREWALL_TABLE = 'filter'
    
    # redefine in sub-class to point to required file
    FILE_FIREWALL_RULES = '/etc/sysconfig/iptables'
    
    def _configureNetworkInterface(self, device, ip, netmask):
        pass

    def configureFireWall(self):
        self._configureFireWallForProxy()
        self._configureFireWallNat()
        self._persistFireWallRules()
    
    def _configureFireWallForProxy(self):
        port = str(self.onePort)
        rules = ({'table':'filter',
                  'rule' :'-A INPUT -s 127.0.0.1 -p tcp -m tcp --dport %s -j ACCEPT' % port},
                 {'table':'filter',
                  'rule' :'-A INPUT -p tcp -m tcp --dport %s -j REJECT --reject-with icmp-port-unreachable' % port})

        if not self._isSetFireWallRulesAll(rules):
            self._setFireWallRulesAll(rules)

    def _configureFireWallNat(self):
        if self.nat.lower() in ['false', 'no', 'off', '0', '']:
            return None

        self._configureFireWallNatNetworking()

        networkWithMask = '%s/%s' % (self.natNetwork, self.natNetmask)
        rules = ({'table':'nat',
                  'rule':'-A POSTROUTING -s %s -d ! %s -j MASQUERADE' % ((networkWithMask,)*2)},
                  {'table':'filter',
                   'rule':'-A FORWARD -d %s -m state --state RELATED,ESTABLISHED -j ACCEPT' % networkWithMask},
                  {'table':'filter',
                   'rule':'-A FORWARD -d %s -j ACCEPT' % networkWithMask})

        if not self._isSetFireWallRulesAll(rules):
            self._setFireWallRulesAll(rules)
 
    def _configureFireWallNatNetworking(self):
        enableIpForwarding()

        device = self.natNetworkInterface
        ip = gatewayIpFromNetAddress(self.natNetwork)
        
        self._configureVirtualNetInterface(device, ip, 
                                           self.natNetmask)

    def _configureVirtualNetInterface(self, device, ip, netmask):
        device = device + ':privlan'

        printDetail('Configuring network interface %s.' % device)
        self._configureNetworkInterface(device, ip, netmask)
        
        printDetail('Starting network interface %s.' % device) 
        self.executeCmd(['ifup', device])

    def _persistFireWallRules(self):
        self._saveFireWallRules(self.FILE_FIREWALL_RULES)

    def _saveFireWallRules(self, filename):
        # back-up
        self.executeCmd(('cp -fp %s %s.LAST'%((filename,)*2)).split(' '))
        
        _,output = self.executeCmdWithOutput(['iptables-save'])
        printDetail('Saving firewall rules to %s.' % filename)
        filePutContent(filename, output)
        os.chmod(filename, 0600)

    def _isSetFireWallRulesAll(self, rules):
        tables = dict.fromkeys([r.get('table', self.DEFAULT_FIREWALL_TABLE) 
                                                        for r in rules]).keys()
        currentRules = self._getFireWallRulesPerTable(tables)
        for ruleSpec in rules:
            if not self._isSetFireWallRule(currentRules, ruleSpec):
                return False
        return True
    
    def _getFireWallRulesPerTable(self, tables=['filter','nat','mangle','raw']):
        rules = {}
        for table in tables:
            rc, output = self.executeCmdWithOutput(('iptables-save -t %s' % 
                                                   table).split(' '))
            if rc != 0:
                raise ExecutionException('iptables-save reported an error:\n%s'% 
                                         output)
            rules.update({table:output})
        return rules

    def _isSetFireWallRule(self, currentRules, ruleSpec):
        rule, table = self._getRuleAndTableFromRuleSpec(ruleSpec)
        rulesInTable = currentRules[table]
        
        if re.search(rule, rulesInTable, re.M):
            return True
        return False
    
    def _setFireWallRulesAll(self, rules):
        self._deleteFireWallRulesAllGiven(rules)
        
        for ruleSpec in rules:
            self._setFireWallRule(ruleSpec)

    def _deleteFireWallRulesAllGiven(self, rules):
        for ruleSpec in rules:
            self._deleteFireWallRule(ruleSpec)

    def _deleteFireWallRule(self, ruleSpec):
        rule, table = self._getRuleAndTableFromRuleSpec(ruleSpec)
        rule = '-D %s' % rule[3:] # remove action; leave chain and rule

        self.executeCmd(('iptables -t %s %s' % (table,rule)).split(' '))        
        
    def _setFireWallRule(self, ruleSpec):
        rule, table = self._getRuleAndTableFromRuleSpec(ruleSpec)
        
        self.executeCmd(('iptables -t %s %s' % (table,rule)).split(' '))        

    def _getRuleAndTableFromRuleSpec(self, ruleSpec):
        return ruleSpec['rule'], \
               ruleSpec.get('table', self.DEFAULT_FIREWALL_TABLE)


FILE_IPFORWARD_HOT_ENABLE = '/proc/sys/net/ipv4/ip_forward'
FILE_IPFORWARD_PERSIST = '/etc/sysctl.conf'

def enableIpForwarding():
    printDetail('Enabling packets forwarding.')
    file(FILE_IPFORWARD_HOT_ENABLE, 'w').write('1')
    appendOrReplaceInFile(FILE_IPFORWARD_PERSIST, 
                          'net.ipv4.ip_forward', 
                          'net.ipv4.ip_forward = 1')
