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


class CIMI(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)

        self._serviceName = 'cimi'
        self._package = 'stratuslab-cimi-server'

    def _installFrontend(self):
        self._installPackages()

    def _setupFrontend(self):
        pass

    def _startServicesFrontend(self):
        self._restartService()

    def _installPackages(self):
        Util.printStep('Removing CIMI server package')
        cmd = 'yum erase -y %s' % self._package
        self._executeExitOnError(cmd)

        Util.printStep('Installing CIMI server package')
        cmd = 'yum install --nogpgcheck -y %s' % self._package
        self._executeExitOnError(cmd)

    def _configure(self):
        pass

    def _restartService(self):
        Util.printStep('Adding %s to chkconfig and restarting' % self._serviceName)
        cmd = 'chkconfig --add %s' % self._serviceName
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % self._serviceName
        Util.execute(cmd.split(' '))

    def _executeExitOnError(self, cmd_str):
        rc, output = Util.execute(cmd_str.split(' '),
                                  withOutput=True,
                                  verboseLevel=self.verboseLevel,
                                  verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
        if rc != 0:
            printError('Failed running: %s\n%s' % (cmd_str, output))
