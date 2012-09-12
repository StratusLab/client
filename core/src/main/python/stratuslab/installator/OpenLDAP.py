#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique
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
import shutil
import stat

import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab import Util
from stratuslab.Util import printError

class OpenLDAP(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)

        self._serviceName = 'slapd'
        self._packages = ['stratuslab-openldap-support']

        self._sharepath = '/usr/share/stratuslab/registration-openldap'

        self._sysconfigLdap = '/etc/sysconfig/ldap'
        self._sysconfigLdapTemplate = '%s/sysconfig/ldap' % self._sharepath

        self._testCertCmd = '%s/scripts/generate-self-signed-certificate.sh' % self._sharepath
        self._certConfigLdif = '%s/ldif/certificates-config.ldif' % self._sharepath

        self._ldapClientConfig = '/etc/openldap/ldap.conf'

        self._openLdapConfig = '/etc/openldap/slapd.d/cn=config/olcDatabase={0}config.ldif'
        self._accessValue  = 'olcAccess: {0}to * by dn.exact=gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth manage by * none'

        self._databaseTemplate = '%s/ldif/cloud-db-defn.ldif' % self._sharepath
        self._completeDatabaseTemplate = 'cloud-db-defn.ldif'

        self._cloudDatabaseSkeleton = '%s/ldif/cloud-data.ldif' % self._sharepath

        self._openLdapAdminDn = 'cn=admin,o=cloud'

        self._nodename = 'localhost'


    def _installFrontend(self):
        self._installPackages()

    def _setupFrontend(self):
        self._configure()

    def _startServicesFrontend(self):
        self._restartService()

    def _installPackages(self):
        Util.printStep('Installing packages')
        self.system.installPackages(self._packages)

    def _configure(self):
        Util.printStep('Configuring OpenLDAP server')

        Util.printStep('Updating sysconfig')
        shutil.copyfile(self._sysconfigLdapTemplate, self._sysconfigLdap)
        Util.appendOrReplaceInFile(self._sysconfigLdap, 'SLAPD_LDAP=', 'SLAPD_LDAP=yes')

        Util.printStep('Setting root account access')
        Util.appendOrReplaceMultilineBlockInFile(self._openLdapConfig, 
                                                 self._accessValue, 
                                                 start='olcAccess: {0}to * by', 
                                                 until='olcAddContentAcl:')

        Util.printStep('(Re-)starting slapd')
        cmd = 'service %s restart' % self._serviceName
        self._executeExitOnError(cmd)

        Util.printStep('Generating test certificate and moving into place')
        self._executeExitOnError(self._testCertCmd)

        self._executeExitOnError('mkdir -p /etc/openldap/cacerts')
        self._executeExitOnError('mv -f cacrt.jks /etc/openldap/cacerts/cacrt.jks')
        self._executeExitOnError('mv -f cacrt.pem /etc/openldap/cacerts/cacrt.pem')
        self._executeExitOnError('mv -f serverkey.pem /etc/openldap/serverkey.pem')
        self._executeExitOnError('mv -f servercrt.pem /etc/openldap/servercrt.pem')

        os.chmod('/etc/openldap/serverkey.pem', stat.S_IRUSR | stat.S_IWUSR)
        self._executeExitOnError('chown ldap:ldap /etc/openldap/serverkey.pem')

        Util.printStep('Updating server config. for generated certs')
        cmd = "ldapmodify -Y EXTERNAL -H ldapi:/// -f %s" % self._certConfigLdif
        Util.execute(cmd.split(' '))

        Util.printStep('Updating client config. for generated certs')
        Util.appendOrReplaceInFile(self._ldapClientConfig,
                                   'TLS_CACERT', 
                                   'TLS_CACERT /etc/openldap/cacerts/cacrt.pem')

        Util.printStep('Creating o=cloud database')
        Util.filePutContent(self._completeDatabaseTemplate,
                            Util.fileGetContent(self._databaseTemplate) % self.__dict__)

        cmd = "ldapadd -Y EXTERNAL -H ldapi:/// -f %s" % self._completeDatabaseTemplate
        Util.execute(cmd.split(' '))

        Util.printStep('Adding cloud database entries')
        cmd = "ldapadd -x -H ldaps://%s -D %s -w %s -f %s" % (self._nodename,
                                                              self._openLdapAdminDn, 
                                                              self.openldapPassword, 
                                                              self._cloudDatabaseSkeleton)
        self._executeExitOnError(cmd)

    def _restartService(self):
        Util.printStep("Adding %s to chkconfig and restarting" % self._serviceName)
        cmd = 'chkconfig --add %s' % self._serviceName
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % self._serviceName
        Util.execute(cmd.split(' '))

    def _executeExitOnError(self, cmd_str):
        rc, output = Util.execute(cmd_str.split(' '), withOutput=True, verboseLevel=self.verboseLevel,
                                  verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
        if rc != 0:
            printError('Failed running: %s\n%s' % (cmd_str, output))
