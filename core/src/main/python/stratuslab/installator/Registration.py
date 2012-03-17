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
import os

import stratuslab.system.SystemFactory as SystemFactory
from stratuslab import Util, Defaults

class Registration(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['stratuslab-registration']
        
    def run(self):
        self._installPackages()
        self._validateParameters()
        self._configure()
        self._restartService('registration')

        
    def _installPackages(self):
        Util.printStep('Installing packages')
        self.system.installPackages(self.packages)


    def _validateParameters(self):
        Util.printStep('Validating parameters')
        if not self.registrationLdapScheme:
            raise ValidationException('registration_ldap_scheme is not defined')
        if not self.registrationLdapHost:
            raise ValidationException('registration_ldap_host is not defined')
        if not self.registrationLdapPort:
            raise ValidationException('registration_ldap_port is not defined')
        if not self.registrationLdapManagerDn:
            raise ValidationException('registration_ldap_manager_dn is not defined')
        if not self.registrationLdapManagerPassword:
            raise ValidationException('registration_ldap_manager_password is not defined')
        if not self.registrationAdminEmail:
            raise ValidationException('registration_admin_email is not defined')
        if not self.registrationMailHost:
            raise ValidationException('registration_mail_host is not defined')
        if not self.registrationMailPort:
            raise ValidationException('registration_mail_port is not defined')
        if not self.registrationMailUser:
            raise ValidationException('registration_mail_user is not defined')
        if not self.registrationMailPassword:
            raise ValidationException('registration_mail_password is not defined')
        if not self.registrationMailSsl:
            raise ValidationException('registration_mail_ssl is not defined')
        if not self.registrationMailDebug:
            raise ValidationException('registration_mail_debug is not defined')
        if not self.registrationSslTruststore:
            self.registrationSslTruststore = ''


    def _configure(self):
        Util.printStep('Creating registration configuration file')
        
        registrationTpl = os.path.join(Util.getTemplateDir(), 'registration.cfg.tpl')
        registrationConfFile = os.path.join(Defaults.ETC_DIR, 'registration.cfg') 
        Util.filePutContent(registrationConfFile,
                            Util.fileGetContent(registrationTpl) % self.__dict__)


    def _restartService(self, service):
        Util.printStep("Adding registration service to chkconfig and restarting")
        cmd = 'chkconfig --add %s' % service
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % service
        Util.execute(cmd.split(' '))
