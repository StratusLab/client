
import time

class Controller():
    
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/var/log/stratuslab-vmc.log'
        self.stderr_path = '/var/log/stratuslab-vmc.log'
        self.pidfile_path =  '/var/run/stratuslab-vmc.pid'
        self.pidfile_timeout = 5
        
    def run(self):
        while True:
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
