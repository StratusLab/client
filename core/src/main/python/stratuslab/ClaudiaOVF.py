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
import datetime
import inspect
import os.path
import time
import unittest
import urllib2
import re

from stratuslab.Monitor import Monitor
from stratuslab.Registrar import Registrar
from stratuslab.Runner import Runner
from stratuslab.Uploader import Uploader
from stratuslab.Creator import Creator
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Exceptions import ExecutionException
from stratuslab.Exceptions import InputException
from stratuslab.ConfigHolder import ConfigHolder
import Util
from stratuslab.marketplace.Downloader import Downloader
import stratuslab.ClaudiaDeploy
import stratuslab.ClaudiaUndeploy
import stratuslab.ClaudiaEvent

import stratuslab.Event as Event
import stratuslab.ClusterTest as ClusterTest
import stratuslab.RegistrationTest as RegistrationTest
import stratuslab.LdapAuthenticationTest as LdapAuthenticationTest
import sys

VM_START_TIMEOUT = 5 * 60 # 5 min

#class Claudia(unittest.TestCase):
class ClaudiaOVF:
    configHolder = None
    testNames = []

    #def setUp(self):
    #    self.vmIds = []
    #    self.image = 'http://appliances.stratuslab.org/images/base/ttylinux-9.7-i486-base/1.2/ttylinux-9.7-i486-base-1.2.img.gz'
  
    def __init__(self, methodName='dummy'):       
        self.vmIds = []
        self.sshKey = '/tmp/id_rsa_smoke_test'
        self.sshKeyPub = self.sshKey + '.pub'
        self.testsToRun = []
        self.quotaCpu = 2
        self.runner = None
        self.imageIdCreateImage = ''

        ClaudiaOVF.configHolder.assign(self)
        self._setFieldsFromEnvVars()


    def _setFieldsFromEnvVars(self):
        self._setSingleFieldFromEnvVar('apprepoUsername', 'STRATUSLAB_APPREPO_USERNAME')
        self._setSingleFieldFromEnvVar('apprepoPassword', 'STRATUSLAB_APPREPO_PASSWORD')
        self._setSingleFieldFromEnvVar('apprepoEndpoint', 'STRATUSLAB_APPREPO_ENDPOINT')
        self._setSingleFieldFromEnvVar('username', 'STRATUSLAB_USERNAME')
        self._setSingleFieldFromEnvVar('password', 'STRATUSLAB_PASSWORD')
        self._setSingleFieldFromEnvVar('requestedIpAddress', 'STRATUSLAB_REQUESTED_IP_ADDRESS')
        self._setSingleFieldFromEnvVar('p12Certificate', 'STRATUSLAB_P12_CERTIFICATE')
        self._setSingleFieldFromEnvVar('p12Password', 'STRATUSLAB_P12_PASSWORD')
        self._exportEndpointIfNotInEnv()
        self._setSingleFieldFromEnvVar('endpoint', 'STRATUSLAB_ENDPOINT')

    def _setSingleFieldFromEnvVar(self, field, env):
        if env in os.environ:
            setattr(self, field, os.environ[env])

    def _exportEndpointIfNotInEnv(self):
        if Util.envEndpoint in os.environ:
            return
        if not self.frontendIp:
            raise ConfigurationException('Missing environment variable %s or configuration parameter frontend_ip' % Util.envEndpoint)
        os.environ[Util.envEndpoint] = self.frontendIp
    
    def doWork(self):        
        task=sys.argv[1]
        if task=="deploy":
            self.deploy()
        elif task=="undeploy":
            self.undeploy()
        elif task=="event":
            self.event()       

    #def _prepareLog(self, logFile):
    #    log = open(logFile, 'aw')
    #    log.write('\n' * 3 + '=' * 60 + '\n')
    #    log.write(str(datetime.datetime.now()) + '\n')
    #    log.write('=' * 60 + '\n' * 3)
    #    return log

    def _checkAttributePresent(self, attrs):
        for attr in attrs:
            if attr not in self.__dict__:
                raise Exception('Missing attribute %s. Missing an option argument?' % attr)

    def deploy(self):
        '''Claudia Deploy'''        
        if self.claudiaCustomer:
            stratuslab.ClaudiaDeploy.ClaudiaDeploy.CLAUDIA_CUSTOMER = self.claudiaCustomer
        if self.claudiaServiceName:
            stratuslab.ClaudiaDeploy.ClaudiaDeploy.CLAUDIA_SERVICENAME = self.claudiaServiceName
        if self.claudiaOvfEndpoint:
            stratuslab.ClaudiaDeploy.ClaudiaDeploy.OVF = self.claudiaOvfEndpoint
            
        deploy=stratuslab.ClaudiaDeploy.ClaudiaDeploy()            
        deploy.doDeploy()

    def undeploy(self):
        '''Claudia Undeploy'''
        if self.claudiaCustomer:
            stratuslab.ClaudiaUndeploy.ClaudiaUndeploy.CLAUDIA_CUSTOMER = self.claudiaCustomer
        if self.claudiaServiceName:
            stratuslab.ClaudiaUndeploy.ClaudiaUndeploy.CLAUDIA_SERVICENAME = self.claudiaServiceName
        
        undeploy=stratuslab.ClaudiaUndeploy.ClaudiaUndeploy()
        undeploy.doUndeploy()

    def event(self):
        '''Claudia event'''
        if self.claudiaEventType:
            stratuslab.ClaudiaEvent.ClaudiaEvent.CLAUDIA_EVENTTYPE = self.claudiaEventType
        if self.claudiaFqn:
            stratuslab.ClaudiaEvent.ClaudiaEvent.CLAUDIA_FQN = self.claudiaFqn
        if self.claudiaValue:
            stratuslab.ClaudiaEvent.ClaudiaEvent.CLAUDIA_VALUE = self.claudiaValue
        
        event=stratuslab.ClaudiaEvent.ClaudiaEvent()
        event.sendEvent()

    #def registrationTest(self):
    #    '''Registration test'''
    #    suite = self._createSuiteFromTestModule(RegistrationTest)
    #    self._executeSuite(suite)
  
    #def ldapAuthenticationTest(self):
    #    '''LDAP authentication test'''
    #    suite = self._createSuiteFromTestModule(LdapAuthenticationTest)
    #    self._executeSuite(suite)
  
    #def _createSuiteFromTestModule(self, module):
    #    suite = unittest.TestSuite()
    #    tests = unittest.TestLoader().loadTestsFromModule(module)
    #    suite.addTests(tests)
    #    return suite
        
    #def _executeSuite(self, suite):
    #    testResult = unittest.TextTestRunner(verbosity=2).run(suite)
    #    self.assertTrue(testResult.wasSuccessful())
