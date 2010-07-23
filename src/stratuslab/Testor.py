import threading
import time
import sys

from stratuslab.UIThread import UIThread
from stratuslab.OneConnector import OneConnector
from stratuslab.Util import fileGetContents

class Testor(object):

    def setCredentials(self, frontend, port, username, password):
        server = 'http://%s:%s/RPC2' % (frontend, port)
        self.cloud = OneConnector(server)
        
    def startVm(self, vmTpl):
        tpl = fileGetContents(vmTpl)
        return self.cloud.startVm(tpl)
    
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
    