#
# Copyright (c) 2013, Centre National de la Recherche Scientifique
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

import time
import string
import os.path
from random import choice
import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab import Util
from stratuslab.Util import printError


class CouchbaseClient(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)

        self._pkgs = ['libcouchbase2-libevent', 'libcouchbase-devel']
        self._deps = ['python-pip', 'gcc']

        self._repofile = '/etc/yum.repos.d/couchbase.repo'
        self._repourl = 'http://packages.couchbase.com/rpm/couchbase-centos62-x86_64.repo'

    def _installFrontend(self):
        self._installPackages()

    def _setupFrontend(self):
        pass

    def _startServicesFrontend(self):
        pass


    def _installNode(self):
	self.system.workOnNode()
        self._installPackagesOnNode()

    def _setupNode(self):
        pass

    def _startServicesNode(self):
        pass


    def _installPackages(self):
        Util.printStep('Setting up Couchbase yum repository')
        cmd = 'curl --output %s %s' % (self._repofile, self._repourl)
        self._executeExitOnError(cmd)

        Util.printStep('Removing Couchbase python client')
        try:
            cmd = 'pip uninstall -y couchbase'
            rc, output = Util.execute(cmd.split(' '),
                                      withOutput=True,
                                      verboseLevel=self.verboseLevel,
                                      verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
            if rc != 0:
                Util.printInfo('Couchbase python client NOT removed')
            else:
                Util.printInfo('Couchbase python client removed')
        except:
            Util.printInfo("Couchbase python client NOT removed")

        Util.printStep('Removing Couchbase C client')
        cmd = 'yum erase -y %s' % ' '.join(self._pkgs)
        self._executeExitOnError(cmd)

        Util.printStep('Installing Couchbase C client')
        cmd = 'yum install -y %s' % ' '.join(self._pkgs)
        self._executeExitOnError(cmd)

        Util.printStep('Installing Couchbase python client dependencies')
        cmd = 'yum install -y %s' % ' '.join(self._deps)
        self._executeExitOnError(cmd)

        Util.printStep('Upgrading pip for Couchbase python client')
        cmd = 'pip install --upgrade'
        self._executeExitOnError(cmd)

        Util.printStep('Installing Couchbase python client')
        cmd = 'pip install couchbase'
        self._executeExitOnError(cmd)


    def _installPackagesOnNode(self):
        Util.printStep('Setting up Couchbase yum repository on node')
        cmd = 'curl --output %s %s' % (self._repofile, self._repourl)
        self._executeOnNodeExitOnError(cmd)

        Util.printStep('Removing Couchbase python client')
        try:
            cmd = 'pip uninstall -y couchbase'
            rc, output = self.system._nodeShell(cmd.split(' '),
                                      withOutput=True,
				      shell=True)	
            if rc != 0:
                Util.printInfo('Couchbase python client NOT removed')
            else:
                Util.printInfo('Couchbase python client removed')
        except:
            Util.printInfo("Couchbase python client NOT removed")

        Util.printStep('Removing Couchbase C client')
        cmd = 'yum erase -y %s' % ' '.join(self._pkgs)
        self._executeOnNodeExitOnError(cmd)

        Util.printStep('Installing Couchbase C client')
        cmd = 'yum install -y %s' % ' '.join(self._pkgs)
        self._executeOnNodeExitOnError(cmd)

        Util.printStep('Installing Couchbase python client dependencies')
        cmd = 'yum install --nogpgcheck -y %s' % ' '.join(self._deps)
        self._executeOnNodeExitOnError(cmd)

        Util.printStep('Installing Couchbase python client')
        cmd = 'pip install couchbase'
        self._executeOnNodeExitOnError(cmd)



    def _configure(self):
        pass

    def _restartService(self):
        pass

    def _executeExitOnError(self, cmd_str):
        rc, output = Util.execute(cmd_str.split(' '),
                                  withOutput=True,
                                  verboseLevel=self.verboseLevel,
                                  verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
        if rc != 0:
            printError('Failed running: %s\n%s' % (cmd_str, output))




    def _executeOnNodeExitOnError(self, cmd_str):
        rc, output = self.system._nodeShell(cmd_str.split(' '),
                                  withOutput=True, 
                                  shell=True)
        if rc != 0:
            printError('Failed running: %s\n%s' % (cmd_str, output))
