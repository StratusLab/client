import os

from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import modulePath
from stratuslab.Util import execute
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Configurable import Configurable
import Util
import stratuslab.system.SystemFactory as SystemFactory

class AppRepo(Configurable):
    '''Perform local installation of an Appliance Repository'''
    
    def __init__(self, configHolder):
        super(AppRepo, self).__init__(configHolder)
        self._verify()

    def _verify(self):
        if self.appRepoUseLdap and not self.appRepoLdapPasswd:
            raise ConfigurationException('LDAP authentication selected but no password for server specified')

        if not self.appRepoUseLdap and not self.appRepoPasswdFile:
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
        system = SystemFactory.getInstance(self.frontendSystem)
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
        
    def _setupWebDav(self):
        self.printDetail('Creating webdav configuration')        
        if (self.appRepoUseLdap):
            httpdConf = fileGetContent('%s/share/template/webdav-ldap.conf.tpl' % modulePath)
            httpdConf = httpdConf % {'imageDir': self.appRepoImageDir,
                                     'ldapSSL': self._getLdapCertString(),
                                     'ldapURL': self.appRepoLdapUrl,
                                     'ldapBind': self.appRepoLdapBind,
                                     'ldapPasswd': self.appRepoLdapPasswd}
        else:
            httpdConf = fileGetContent('%s/share/template/webdav.conf.tpl' % modulePath)
            httpdConf = httpdConf % {'imageDir': self.appRepoImageDir,
                                     'passwd': self.appRepoPasswdFile}	   

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
#        repoConfig = fileGetContent('%s/share/template/stratuslab.repo.cfg.tpl' % modulePath)
#        repoConfig = repoConfig % {'repo_structure': self.repoStructure,
#                                     'repo_filename': self.repoFilename}
#        filePutContent('%s/.stratuslab/stratuslab.repo.cfg' % self.appRepoImageDir, repoConfig)

    def _getLdapCertString(self):
        if self.appRepoLdapCert:
            ldapCertString = 'LDAPVerifyServerCert on\nLDAPTrustedGlobalCert CA_BASE64 %s\nLDAPTrustedMode SSL\n' % self.ldapCert
        else:
            ldapCertString = ''
            
        return ldapCertString

    def _execute(self, cmd):
        return execute(cmd, verboseLevel=self.verboseLevel)
    
    def _setup(self):
        self._setupWebServer()
        self._setupImageRepo()

    def _setupWebServer(self):
        pass
