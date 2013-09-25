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
import traceback

import stratuslab.controller.util as util


class BaseController():
    def __init__(self, service_name, default_cfg_docid, pause=10):
        """
        The base class for controller daemons.  Subclasses must
        provide the service_name, default_cfg_docid, and an optional
        pause time (in seconds).

        The daemon will read the Couchbase configuration, initial the
        connection to the database, read the service configuration,
        validate the service configuration, then enter the processing
        loop.

        The processing loop will emit a heartbeat message for the
        service, then collect, claim, and process jobs.  This loop is
        repeated until the daemon is stopped.

        The daemon's activity is logged to syslog.  The logger for the
        service has the same name as the service_name.
        """

        self.service_name = service_name
        self.default_cfg_docid = default_cfg_docid
        self.pause = pause
        self.executor = '%s/%s' % (self.service_name, socket.getfqdn())
        self.heartbeat_docid = 'Heartbeat/%s' % self.executor

        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = '/var/run/%s.pid' % self.service_name
        self.pidfile_timeout = 5

    def _setup_logger(self, logger_name):

        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        handler = logging.handlers.SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(name)s :: %(levelname)s :: %(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        return logging.getLogger(logger_name)

    def run(self):

        self.logger = self._setup_logger(self.service_name)

        self.logger.info('starting')

        try:
            cb_cfg = util.read_cb_cfg(self.service_name, self.default_cfg_docid)
            self.logger.info('read Couchbase configuration: %(host)s, %(bucket)s' % cb_cfg)
        except Exception as e:
            self.logger.error('error reading Couchbase configuration: %s' % e)
            return 1

        try:
            self.cb = util.init_cb_client(cb_cfg)
            self.logger.info('created Couchbase client')
        except Exception as e:
            self.logger.error('error creating Couchbase client: %s' % e)
            return 1

        self.logger.info('finished initialization')

        try:

            while True:

                time.sleep(self.pause)

                try:
                    self.cfg = util.get_service_cfg(self.cb, cb_cfg['cfg_docid'])
                except Exception as e:
                    self.logger.error('error reading service configuration: %s' % e)
                    continue

                try:
                    self._validate_service_cfg(self.cfg)
                    util.heartbeat(self.cb, self.heartbeat_docid)
                except Exception as e:
                    msg = 'service configuration error: %s' % e
                    util.heartbeat(self.cb, self.heartbeat_docid, status='ERROR', message=msg)
                    self.logger.error(msg)
                    continue

                for job in self._jobs():
                    job_id = self._job_id(job)
                    self.logger.info('evaluating %s' % job_id)
                    if self._claim(job):
                        self.logger.info('claimed %s' % job_id)
                        self._execute(job)

        except SystemExit:
            util.heartbeat(self.cb, self.heartbeat_docid, status='STOPPED', message='normal shutdown')
            self.logger.info('terminated')

        except Exception as e:
            util.heartbeat(self.cb, self.heartbeat_docid, status='ERROR', message=str(e))
            self.logger.error('unexpected exception: %s' % traceback.format_exc())

    def _job_id(self, job):
        try:
            return str(job['id'])
        except:
            return '< ID_UNKNOWN >'

    def _validate_service_cfg(self, cfg):
        """
        This method validates the service configuration read from the
        database.  This method should raise an exception with a
        reasonable message if the service configuration is not valid.
        This default implementation is a no-op.
        """
        pass

    def _jobs(self):
        """
        Used to select jobs from the database.  The method should
        return an array of the selected jobs.  This default
        implementation always returns an empty list.
        """
        return []

    def _claim(self, job):
        """
        Used to evaluate whether a job should be treated by this
        controller or not.  If the job is claimed, then the method
        should update the job with the new status and return True.  It
        should return false otherwise.  Implementations must be aware
        that other controllers may be trying to claim the same job.
        """
        return False

    def _execute(self, job):
        """
        Actually execute the work associated with the given job.  This
        method is responsible for updating the status of the job when
        it has completed.  This implementation is a no-op and does not
        modify the given job.
        """
        pass
