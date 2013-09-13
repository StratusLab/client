
import socket
import time

from stratuslab.api.controller import Util

class Controller():

    SEC_IN_DAY = 24 * 60 * 60
    
    def __init__(self):
        cb_cfg = Util.read_cb_cfg()

        self.cb = Util.get_cb_client(host=cb_cfg.get('host'),
                                     bucket=cb_cfg.get('bucket'),
                                     password=cb_cfg.get('password'))

        # needs to define query for jobs, etc.
        cfg = self.cb.get(cb_cfg.get('cfg_docid'))

        self.heartbeat_docid = 'Heatbeat/pdc/%s' % socket.getfqdn()

        self.stdin_path = '/dev/null'
        self.stdout_path = '/var/log/stratuslab-pdc.log'
        self.stderr_path = '/var/log/stratuslab-pdc.log'
        self.pidfile_path =  '/var/run/stratuslab-pdc.pid'
        self.pidfile_timeout = 5
        
    def run(self):
        while True:
            Util.heartbeat(self.cb, self.heartbeat_docid)

            for job in self._get_jobs():
                if self._claim(job):
                    self._execute(job)

            time.sleep(10)

    def _get_jobs(self):
        return ['dummy']

    def _claim(self, job):
        return True

    def _execute(self, job):
        print 'Executing job: %s' % job
