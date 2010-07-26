import threading
import time

from stratuslab.UIThread import UIThread
from stratuslab.OneConnector import OneConnector

class Testor(object):

    def setCredentials(self, frontend, port, username, password):
        server = 'http://%s:%s/RPC2' % (frontend, port)
        self.cloud = OneConnector(server)
        self.cloud.setCredentials(username, password)
        
    def startVm(self, vmTpl):
        return self.cloud.startVm(vmTpl)
    
    def waitUntilVmRunningOrTimeout(self, vmId, timeout):
        event = threading.Event()
        thread = UIThread(event, timeout, 'Starting VM', '')
        thread.start()
        
        while self.getVmState(vmId) != 'running' and event.isSet() == False:
            time.sleep(2)
        
        if event.isSet():
            return False
        else:            
            event.set()
            return True
        
    def getVmState(self, vmId):
        return self.cloud.getVmState(vmId)
    
    def deleteVm(self, vmId):
        self.cloud.actionOnVm(vmId, 'shutdown')
    