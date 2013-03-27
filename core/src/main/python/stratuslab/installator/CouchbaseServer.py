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
import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab import Util
from stratuslab.Util import printError

from couchbase.client import Couchbase

class CouchbaseServer(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)

        self._serviceName = 'couchbase-server'
        self._packages = ['couchbase-server']

        self._cb_username = 'admin'
        self._cb_password = 'ADMIN4'

        self._bucket_name = 'test_bucket'

        self.couchbase_cli = '/opt/couchbase/bin/couchbase-cli %s -c 127.0.0.1:8091 %s'


    def _installFrontend(self):
        self._installPackages()

    def _setupFrontend(self):
        self._configure()

    def _startServicesFrontend(self):
        self._restartService()

    def _installPackages(self):
        Util.printStep('Configuring machine to use Couchbase yum repository')
        self._executeExitOnError('wget -O/etc/yum.repos.d/couchbase.repo http://packages.couchbase.com/rpm/couchbase-centos62-x86_64.repo')

        Util.printStep('Installing packages')
        self.system.installPackages(self._packages)

    def _configure(self):

        Util.printStep('(Re-)starting Couchbase')
        cmd = 'service %s restart' % self._serviceName
        self._executeExitOnError(cmd)

        time.sleep(5)

        Util.printStep('Set Couchbase data location')
        cmd = self.couchbase_cli % ('node-init', '--node-init-data-path=/opt/couchbase/var/lib/couchbase/data')
        self._executeExitOnError(cmd)

        Util.printStep('Create Couchbase bucket')
        cmd = self.couchbase_cli % ('bucket-create', '--bucket-test_bucket --bucket-type=couchbase --bucket-password=TEST --bucket-ramsize=400 --bucket-replica=1')
        self._executeExitOnError(cmd)

        Util.printStep('Initialize Couchbase admin account')
        self._executeExitOnError(self.couchbase_cli % ('cluster-init', '--cluster-init-username=admin --cluster-init-password=ADMIN4'))


    def _restartService(self):
        Util.printStep("Adding %s to chkconfig and restarting" % self._serviceName)
        cmd = 'chkconfig --add %s' % self._serviceName
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % self._serviceName
        Util.execute(cmd.split(' '))

    def _executeExitOnError(self, cmd_str):
        rc, output = Util.execute(cmd_str.split(' '), withOutput=True, verboseLevel=self.verboseLevel,
                                  verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
        if rc != 0:
            printError('Failed running: %s\n%s' % (cmd_str, output))
