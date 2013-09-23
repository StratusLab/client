#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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

import logging
import logging.handlers
import socket
import time

import stratuslab.controller.util as util


class Controller():
    SERVICE_NAME = 'pdc'

    DEFAULT_CFG_DOCID = 'Configuration/pdc'

    def __init__(self):

        self.heartbeat_docid = 'Heartbeat/%s/%s' % (self.SERVICE_NAME, socket.getfqdn())

        self.log_path = '/var/log/stratuslab-pdc.log'
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = '/var/run/stratuslab-pdc.pid'
        self.pidfile_timeout = 5

    def run(self):

        logging.basicConfig(format='%(asctime)s :: %(message)s')
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.handlers.TimedRotatingFileHandler(self.log_path,
                                                            when='midnight',
                                                            interval=1,
                                                            backupCount=7)
        logger.addHandler(handler)

        logger.info('starting')

        cb_cfg = util.read_cb_cfg(self.SERVICE_NAME, self.DEFAULT_CFG_DOCID)

        cb = util.init_cb_client(cb_cfg)

        cfg = util.get_service_cfg(cb, cb_cfg['cfg_docid'])

        logger.info('finished initialization')

        while True:
            util.heartbeat(cb, self.heartbeat_docid)

            for job in self._get_jobs():
                logger.info('evaluating job %s' % job)
                if self._claim(job):
                    logger.info('claimed job %s' % job)
                    self._execute(job)

            time.sleep(10)

    def _get_jobs(self):
        return ['dummy']

    def _claim(self, job):
        return True

    def _execute(self, job):
        print 'Executing job: %s' % job
