import sys
import threading
import time

class UIThread(threading.Thread,object):
    def __init__(self,event,timeout=30,startMessage='',endMessage='',stdout=None,stderr=None):
        super(UIThread,self).__init__()
        if stdout != None:
            self.stdout = stdout
        else:
            self.stdout = sys.stdout
        if stderr != None:
            self.stderr = stderr
        else:
            self.stderr = sys.stderr
        self.event = event
        self.startMsg = startMessage
        self.endMsg = endMessage
        self.timeout = timeout

    def run(self):
        noOfTickForDots = 2
        ticks = 0
        while not self.event.isSet():
            time.sleep(1)
            self.timeout -= 1
            mainThread = threading.currentThread()
            if self.timeout == 0:
                self.event.set()
            if mainThread.isAlive() is False:
                sys.exit(1)
            if ticks >= noOfTickForDots:
                if ticks == noOfTickForDots:
                    self.stdout.write('\n%s' % self.startMsg)
                self.stdout.write('.')
                if ticks+len(self.startMsg) % 80 == 0:
                    self.stdout.write('\n')
                self.stdout.flush()
            ticks += 1
        if ticks > noOfTickForDots:
            sys.stdout.write('%s\n' % self.endMsg)
            self.stdout.flush()
            