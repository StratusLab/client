import os

from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import modulePath
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import execute
from stratuslab.Util import assignAttributes

class AppRepo(object):
    
    def __init__(self, options):
        assignAttributes(self, options)

    def getLdapCertString(self):
        if self.ldapCert:
            ldapCertString = 'LDAPVerifyServerCert on\nLDAPTrustedGlobalCert CA_BASE64 %s\nLDAPTrustedMode SSL\n' % self.ldapCert
        else:
            ldapCertString = ''
            
        return ldapCertString

    def install(self):
        printAction('Installing image repository')
        printStep('Creating webdav configuration')        
        if (self.ldap):
            httpd_conf = fileGetContent('%s/share/template/webdav-ldap.conf.tpl' % modulePath)
            httpd_conf = httpd_conf % {'imageDir': self.imageDir,
                                       'ldapSSL': self.getLdapCertString(),
                                       'ldapURL': self.ldapUrl,
                                       'ldapBind': self.ldapBind,
                                       'ldapPasswd': self.ldapPasswd
                                        }
        else:
            httpd_conf = fileGetContent('%s/share/template/webdav.conf.tpl' % modulePath)
            httpd_conf = httpd_conf % {'imageDir': self.imageDir,
                                       'passwd': self.passwdFile
                                      }	   

        filePutContent('%s/conf.d/webdav.conf' % self.apacheHome, httpd_conf)

        if self.create:
            printStep('Creating repository directory structure')
            if not os.path.exists('%s/eu/stratuslab/appliances' % self.imageDir):
                os.makedirs('%s/eu/stratuslab/appliances' % self.imageDir)
                os.makedirs('%s/eu/stratuslab/appliances/grid' % self.imageDir)
                os.makedirs('%s/eu/stratuslab/appliances/base' % self.imageDir)

            if not os.path.exists('%s/.stratuslab' % self.imageDir):
                os.makedirs('%s/.stratuslab' % self.imageDir)
            execute('chown','-R','apache.apache', '%s/eu' % self.imageDir)            

        printStep('Creating repository configuration file')
        repo_config = fileGetContent('%s/share/template/stratuslab.repo.cfg.tpl' % modulePath)
        repo_config = repo_config % {'repo_structure': self.repo_structure,
                                     'repo_filename': self.repo_filename}
        filePutContent('%s/.stratuslab/stratuslab.repo.cfg' % self.imageDir, repo_config)
