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

import stratuslab.system.SystemFactory as SystemFactory
from stratuslab import Util, Defaults
from shutil import copyfile
from shutil import move

class OpenLDAP(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['stratuslab-openldap-support']
        
    def run(self):
        self._installPackages()
        self._configure()
        self._restartService('slapd')
        
    def _installPackages(self):
        Util.printStep('Installing packages')
        self.system.installPackages(self.packages)

    def _configure(self):
        Util.printStep('Creating LDAP configuration files')

        sharepath = '/usr/share/stratuslab/registration-openldap'

        copyfile(('%s/sysconfig/ldap' % sharepath),
                 '/etc/sysconfig/ldap')

        Util.appendOrReplaceInFile('/etc/sysconfig/ldap', 'SLAPD_LDAP=', 'SLAPD_LDAP=yes')

        Util.appendOrReplaceInFile('/etc/openldap/slapd.d/cn=config/olcDatabase={0}config.ldif',
                                   'olcAccess:',
                                   'olcAccess: {0}to * by dn.exact=gidNumber=0+uidNumber=0,cn=peercred,cn=external,cn=auth manage by * none')

        cmd = 'service %s start' % service
        Util.execute(cmd.split(' '))

        cmd = '%s/scripts/generate-self-signed-certificate.sh' % sharepath
        Util.execute(cmd.split(' '))

        move('cacrt.pem', '/etc/openldap/cacerts/')
        move('serverkey.pem', '/etc/openldap/')
        move('servercrt.pem', '/etc/openldap/')

        cmd = "ldapmodify -Y EXTERNAL -H ldapi:/// -f %s/ldif/certificates-config.ldif" % sharedir
        Util.execute(cmd.split(' '))

        Util.appendOrReplaceInFile('/etc/openldap/ldap.conf',
                                   'TLS_CACERT', 
                                   'TLS_CACERT /etc/openldap/cacerts/cacrt.pem')

        databaseDefinition = '%s/ldif/cloud-db-defn.ldif' % sharedir
        copy(databaseDefinition, 'cloud-db-defn.ldif')
        Util.appendOrReplaceInFile('cloud-db-defn.ldif', 
                                   'olcRootPW', 
                                   ('olcRootPW: %s' % self.openldapPasswordHash))

        databaseTemplate = '%s/ldif/cloud-db-defn.ldif' % sharedir
        completeDatabaseTemplate = 'cloud-db-defn.ldif' 
        Util.filePutContent(completeDatabaseTemplate,
                            Util.fileGetContent(databaseTemplate) % self.__dict__)

        cmd = "ldapadd -Y EXTERNAL -H ldapi:/// -f %s" % completeDatabaseTemplate
        Util.execute(cmd.split(' '))

        cmd = "ldapadd -x -H ldaps://localhost -D cn=admin,o=cloud -w %s -f %s/ldif/cloud-data.ldif" % (self.openldapPassword, sharedir)
        Util.execute(cmd.split(' '))


    def _restartService(self, service):
        Util.printStep("Adding slapd to chkconfig and restarting")
        cmd = 'chkconfig --add %s' % service
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % service
        Util.execute(cmd.split(' '))
