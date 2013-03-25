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

import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab import Util
from stratuslab.Util import printError

from couchbase.client import Couchbase

class Couchbase(Installator):

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

        Util.printStep('Initialize Couchbase admin account')
        self._executeExitOnError(self.couchbase_cli % ('cluster-init', '--cluster-init-username=admin --cluster-init-password=ADMIN4'))

        Util.printStep('Create Couchbase bucket')
        cb = Couchbase('localhost:8091',
                       username=self._cb_username,
                       password=self._cb_password)
        if not (self._bucket_name in cb.buckets()):
            cb.create(self._bucketname, ram_quota_mb=400, replica=1)

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
