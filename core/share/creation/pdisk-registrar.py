#!/usr/bin/env python
import sys
from subprocess import Popen
from pickle import loads, dump
from optparse import OptionParser

class PDiskEntry(object):
    def __init__(self, portal, node, vmId):
        self.portal = portal
        self.node = node
        self.vmId = vmId
        
class PDiskRegistrar(object):
    INSTANCES, VMS = 0, 1
    PORTAL, NODE = 0, 1
    
    def __init__(self):
        self.instances = {}
        self.vms = {}
        self.instancesFile = '/tmp/pdisk.p'
        self.detacheCmd = '/usr/sbin/detach-persistent-disk.sh'
        self._loadInstances()
    
    def _touch(self):
        fd = open(self.instancesFile, 'a+')
        fd.close()
    
    def _loadInstances(self):
        self._touch()
        fd = open(self.instancesFile, 'rb')
        data = fd.read()
        fd.close()
        if data:
            db = loads(data)
            self.instances = db[self.INSTANCES]
            self.vms = db[self.VMS]
        
    def _saveInstances(self):
        print 'Saving to pickle'
        db = [self.instances, self.vms]
        fd = open(self.instancesFile, 'wb')
        dump(db, fd)
        fd.close()
        
    def _getDiskInstances(self, uuid):
        if uuid not in self.instances:
            self.instances[uuid] = []
        return self.instances[uuid]
    
    def _removeEntry(self, diskUuid, vmId):
        '''If node address returned, disk should be unmounted'''
        # As this is a prototype we don't check that multiple portal have same disk UUID
        entries = self.instances[diskUuid][:]
        nodeAddr = None
        portalAddr = None
        nodes = []
        for entry in entries:
            if entry.vmId == vmId:
                nodeAddr = entry.node
                portalAddr = entry.portal
                self.instances[diskUuid].remove(entry)
                if not self.instances[diskUuid]:
                    del self.instances[diskUuid]
                    break
            elif entry.node not in nodes:
                nodes.append(entry.node)
        if nodeAddr in nodes:
            return None
        else:
            return (portalAddr, nodeAddr)
                
    def _detachDisk(self, node, uuid, portal):
        print 'detaching disk %s on %s from %s' % (uuid, portal, node)
        cmd = ['ssh', node, self.detacheCmd, uuid, portal]
        p = Popen(cmd)
        p.wait()
        
    def addInstance(self, portal, node, vmId, diskUuid):
        print 'Adding %s using %s on %s from %s' % (vmId, diskUuid, portal, node)
        instance = self._getDiskInstances(diskUuid)
        entry = PDiskEntry(portal, node, vmId)
        instance.append(entry)
        self.vms[vmId] = diskUuid
        self._saveInstances()
        
    def deleteInstance(self, vmId):
        uuid = self.vms.get(vmId, None)
        if not uuid:
            print 'VM %s not in DB' % vmId
            return
        del self.vms[vmId]
        ret = self._removeEntry(uuid, vmId)
        if ret:
            portal = ret[self.PORTAL]
            node = ret[self.NODE]
            self._detachDisk(node, uuid, portal)
        else:
            print 'disk % still in use' % uuid
        self._saveInstances()
        
def checkOptions(options, vmId):
    if not vmId:
        print 'VM ID not specified'
        sys.exit(1)
    if not options.detach and (not options.portal or 
                               not options.node or 
                               not options.uuid):
        print 'Hostname option require UUID option and portal option and vice versa'
        sys.exit(1)
        
if __name__ == '__main__':
    usage = 'usage: %prog VM_ID [options]'
    parser = OptionParser(usage=usage)
 
    parser.add_option("-p", "--portal", dest="portal", default=None,
                      help="Portal from where is mounted the pdisk", metavar="ADDRESS")
    parser.add_option("-n", "--node", dest="node", default=None,
                      help="Node where is mounted the pdisk", metavar="ADDRESS")
    parser.add_option("-u", "--uuid", dest="uuid", default=None,
                      help="Disk UUID being mounted", metavar='UUID')
    parser.add_option("-d", "--detach", dest="detach", default=False,
                      help="Detach the specified disk UUID", action='store_true')
    
    (options, vmId) = parser.parse_args()
    
    checkOptions(options, vmId)
    
    registrar = PDiskRegistrar()
    
    if options.portal:
        registrar.addInstance(options.portal, options.node, int(vmId[0]), options.uuid)
    else:
        registrar.deleteInstance(int(vmId[0]))
