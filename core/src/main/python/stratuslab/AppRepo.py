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
import os

from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import execute
import stratuslab.Util as Util
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Configurable import Configurable
import stratuslab.system.SystemFactory as SystemFactory

class AppRepo(Configurable):
    '''Perform local installation of an Appliance Repository'''
    
    def __init__(self, configHolder):
        super(AppRepo, self).__init__(configHolder)
        self.configHolder = configHolder

    def verify(self):
        if self.appRepoUseLdap and not self.appRepoLdapPasswd:
            raise ConfigurationException('LDAP authentication selected but no password for server specified')

        if not self.appRepoUseLdap and not self.appRepoHttpdPasswdFile:
            raise ConfigurationException('No password file specified')

    def run(self):
        installAndSetup = not (self.onlySetup or self.onlyInstall)
        install = self.onlyInstall or installAndSetup
        if install:
            self._install()
        setup = self.onlySetup or installAndSetup
        if setup:
            self._setup()
    
    def _install(self):
        self._installWebServer()
        self._installImageRepo()

    def _installWebServer(self):
        self.printStep('Installing web server (apache2 / httpd)')
        system = SystemFactory.getSystem(self.frontendSystem, self.configHolder)
        system.installPackages([system.packages['apache2'].packageName])
        if not os.path.exists(self.appRepoApacheHome):
            raise ConfigurationException('Apache home not found: %s' % self.appRepoApacheHome)

    def _installImageRepo(self):
        pass
    
    def _setupImageRepo(self):
        self.printStep('Setting-up image repository')
        self._setupWebDav()
        self._createRepoStructure()
        self._createRepoConfig()
        self._restartWebServer()
 
    def _setupWebDav(self):
        self.printDetail('Creating webdav configuration')        
        if (self.appRepoUseLdap):
            httpdConf = fileGetContent(Util.shareDir + 'template/webdav-ldap.conf.tpl')
            httpdConf = httpdConf % {'imageDir': self.appRepoImageDir,
                                     'ldapSSL': self._getLdapCertString(),
                                     'ldapURL': self.appRepoLdapUrl,
                                     'ldapBind': self.appRepoLdapBind,
                                     'ldapPasswd': self.appRepoLdapPasswd}
        else:
            httpdConf = fileGetContent(Util.shareDir + 'template/webdav.conf.tpl')
            httpdConf = httpdConf % {'imageDir': self.appRepoImageDir,
                                     'passwd': self.appRepoHttpdPasswdFile}	   

        filePutContent('%s/conf.d/webdav.conf' % self.appRepoApacheHome, httpdConf)

    def _createRepoStructure(self):
        self.printDetail('Creating repository directory structure')
        if not os.path.exists('%s/eu/stratuslab/appliances' % self.appRepoImageDir):
            os.makedirs('%s/eu/stratuslab/appliances' % self.appRepoImageDir)
            os.makedirs('%s/eu/stratuslab/appliances/grid' % self.appRepoImageDir)
            os.makedirs('%s/eu/stratuslab/appliances/base' % self.appRepoImageDir)

        if not os.path.exists('%s/.stratuslab' % self.appRepoImageDir):
            os.makedirs('%s/.stratuslab' % self.appRepoImageDir)
        self._execute(['chown', '-R', 'apache.apache', '%s/eu' % self.appRepoImageDir])

    def _createRepoConfig(self):
        self.printDetail('Creating repository configuration file')
        repoConfig = fileGetContent(Util.shareDir + 'template/stratuslab.repo.cfg.tpl')
        repoConfig = repoConfig % {'repo_structure': self.appRepoStructure,
                                     'repo_filename': self.appRepoFilename}
        filePutContent('%s/.stratuslab/stratuslab.repo.cfg' % self.appRepoImageDir, repoConfig)

    def _getLdapCertString(self):
        if self.appRepoLdapCert:
            ldapCertString = 'LDAPVerifyServerCert on\nLDAPTrustedGlobalCert CA_BASE64 %s\nLDAPTrustedMode SSL\n' % self.appRepoLdapCert
        else:
            ldapCertString = ''
            
        return ldapCertString

    def _restartWebServer(self):
        self.printDetail('Restarting web server (apache2 / httpd)\n')
        system = SystemFactory.getSystem(self.frontendSystem, self.configHolder)
        self._execute(['/etc/init.d/%s' % system.packages['apache2'].packageName, 'stop'])
        self._execute(['/etc/init.d/%s' % system.packages['apache2'].packageName, 'start'])

    def _execute(self, cmd):
        return execute(cmd, verboseLevel=self.verboseLevel)
    
    def _setup(self):
        self._setupWebServer()
        self._setupImageRepo()

    def _setupWebServer(self):
        pass
