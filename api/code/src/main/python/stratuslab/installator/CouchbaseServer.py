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
import os
import os.path
from random import choice
import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab import Util
from stratuslab.Util import printError


class CouchbaseServer(Installator):

    @staticmethod
    def _generate_password():
        chars = string.letters + string.digits
        length = 8
        return ''.join([choice(chars) for _ in range(length)])

    @staticmethod
    def _cb_cmd(func, host, options):
        opts = ' '.join(options)
        cmd = '/opt/couchbase/bin/couchbase-cli %s -c %s:8091 %s' % (func, host, opts)
        return cmd

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)

        self._serviceName = 'couchbase-server'
        self._packages = ['couchbase-server']

        self._cb_cluster_username = 'admin'
        self._cb_cluster_password = CouchbaseServer._generate_password()
        self._cb_cluster_password_path = '/opt/couchbase/cluster-password.txt'

    def _installFrontend(self):
        self._installPackages()

    def _setupFrontend(self):
        if os.path.exists(self._cb_cluster_password_path):
            Util.printStep('%s exists; skipping Couchbase configuration' % self._cb_cluster_password_path)
        else:
            self._configure()

    def _startServicesFrontend(self):
        self._restartService()

    def _installPackages(self):
        Util.printStep('Installing Couchbase packages')
        self.system.installPackages(self._packages)

    def _configure(self):
        Util.printStep('(Re-)starting Couchbase')
        cmd = 'service %s restart' % self._serviceName
        self._executeExitOnError(cmd)

        time.sleep(5)

        Util.printStep('Set Couchbase data location')
        options = ['--node-init-data-path=/opt/couchbase/var/lib/couchbase/data']
        cmd = CouchbaseServer._cb_cmd('node-init', self.frontendIp, options)
        self._executeExitOnError(cmd)

        Util.printStep('Create default Couchbase bucket')
        options = ['--bucket=default',
                   '--bucket-type=couchbase',
                   '--bucket-ramsize=400',
                   '--bucket-replica=1']
        cmd = CouchbaseServer._cb_cmd('bucket-create', self.frontendIp, options)
        self._executeExitOnError(cmd)

        Util.printStep('Initialize Couchbase admin account')
        options = ['--cluster-init-username=%s' % self._cb_cluster_username,
                   '--cluster-init-password=%s' % self._cb_cluster_password]
        cmd = CouchbaseServer._cb_cmd('cluster-init', self.frontendIp, options)
        self._executeExitOnError(cmd)

        Util.printStep('Saving cluster password in %s' % self._cb_cluster_password_path)
        with open(self._cb_cluster_password_path, 'w') as f:
            f.write(self._cb_cluster_password + "\n")

        Util.printStep('Reducing read access to password file')
        os.chmod(self._cb_cluster_password_path, 0400)

    def _restartService(self):
        Util.printStep('Adding %s to chkconfig and restarting' % self._serviceName)
        cmd = 'chkconfig --add %s' % self._serviceName
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % self._serviceName
        Util.execute(cmd.split(' '))

    def _executeExitOnError(self, cmd_str):
        rc, output = Util.execute(cmd_str.split(' '), withOutput=True, verboseLevel=self.verboseLevel,
                                  verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
        if rc != 0:
            printError('Failed running: %s\n%s' % (cmd_str, output))
