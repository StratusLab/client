#!/usr/bin/env python
# The goal of this script is to test StratusLab with only CLI user command,
# to make sure an user would encounter problem will user the cloud

#Requirements : Define  environements variables :
#export STRATUSLAB_MARKETPLACE=http://onehost-2.lal.in2p3.fr:8081/marketplace/
#export STRATUSLAB_PERSISTENT_STORAGE=http://onehost-2.lal.in2p3.fr:8082/persistent-disk/disks/
#export STRATUSLAB_USERNAME=test
#export STRATUSLAB_PASSWORD=test
#export STRATUSLAB_P12_CERTIFICATE=/Users/airaj/gridcert/yourgridcert.p12
#export STRATUSLAB_P12_PASSWORD=####
#export STRATUSLAB_ENDPOINT=onehost-4.lal.in2p3.fr
#export STRATUSLAB_IMAGE='http://appliances.stratuslab.eu/images/base/ttylinux-9.7-i486-base/1.3/ttylinux-9.7-i486-base-1.3.img.gz'

import os
import subprocess
import time 
import urllib2
import inspect
import sys

try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise Exception("Failed to import ElementTree from any known place")
  
   
class Tutorial:
    VM_STATUS_TIMEOUT = 5 * 60 # 5 min
    VM_PING_TIMEOUT = 3 * 60 # 3 min
    RETURN_OUT, RETURN_CODE = 0, 1
    
    def __init__(self):
        self.sshKey = '/tmp/tutorial_test/id_rsa'
        self.sshKeyPub = self.sshKey + '.pub'
        self.vmId = None

        self._setFieldsFromEnvVars()
        self.fakeImage = 'dummy.img'
        self.fakeMetadata = 'ttylinux-9.3-i686-base-1.0.xml'
        self.claudiaOvfEndpoint = "http://84.21.173.141:8080/telefonica.xml" 

    def _setFieldsFromEnvVars(self):
        self._setSingleFieldFromEnvVar('image', 'STRATUSLAB_IMAGE')
        self._setSingleFieldFromEnvVar('marketplace', 'STRATUSLAB_MARKETPLACE')
        self._setSingleFieldFromEnvVar('username', 'STRATUSLAB_USERNAME')
        self._setSingleFieldFromEnvVar('password', 'STRATUSLAB_PASSWORD')
        self._setSingleFieldFromEnvVar('p12Certificate', 'STRATUSLAB_P12_CERTIFICATE')
        self._setSingleFieldFromEnvVar('p12Password', 'STRATUSLAB_P12_PASSWORD')
        self._setSingleFieldFromEnvVar('endpoint', 'STRATUSLAB_ENDPOINT')
        self._setSingleFieldFromEnvVar('pdiskEndpoint', 'STRATUSLAB_PDISK_ENDPOINT')
        self._setSingleFieldFromEnvVar('pdiskUsername', 'STRATUSLAB_PDISK_USERNAME')
        self._setSingleFieldFromEnvVar('pdiskPassword', 'STRATUSLAB_PDISK_PASSWORD')

    def _setSingleFieldFromEnvVar(self, field, env):
        setattr(self, field, os.environ.get(env, ''))
            
    def printAttributes(self):
        for elem in self.__dict__:
            if not inspect.ismethod(getattr(self, elem)):
                print '\t%s = %s' % (elem, getattr(self, elem))
                
    def _execute(self, cmd, returnType=None, exit=True, quiet=False, shell=False):
        self.printCmd(' '.join(cmd))
        if quiet:
            devNull = open('/dev/null', 'w')
            stdout = devNull
            stderr = devNull
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE
        p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
        p.wait()
        if quiet:
            devNull.close()
        if returnType:
            return p.returncode
        else:
            out = p.stdout.read()
            err = p.stderr.read()
            if p.returncode == 0:
                if not quiet:
                    if out:
                        self.printAndFlush(out + '\n')
                    if err:
                        self.printAndFlush(err + '\n')
                return out
            else:
                self.printAndFlush('  [ERROR] Error executing command!\n')
                if out:
                    self.printAndFlush(out + '\n')
                if err:
                    self.printAndFlush(err + '\n')
                if exit:
                    raise Exception
    
    def _ping(self, ip, number=1):
        return self._execute(['ping', '-q', '-c', str(number), ip.strip()],
                             self.RETURN_CODE, exit=False, quiet=True) == 0
    
    def _pingUntilTimeout(self, vmIp):
        start = time.time()
        pinged = False
        while not pinged and ((time.time() - start) < self.VM_PING_TIMEOUT):
            pinged = self._ping(vmIp)
            time.sleep(5)
        return pinged
    
    def generateDummyImage(self, filename, size=10):
        self._execute(['dd', 'if=/dev/zero', 'of=%s' % filename, 'bs=1024', 'count=%s' % size])    
    
    def _readRemoteFile(self, url):
        fd = self._wget(url)
        return fd.read()
    
    def _wget(self, url):
        return urllib2.urlopen(url)
    
    def generateSshKeyPair(self, keyFilename):
        try:
            os.remove(keyFilename)
            os.remove(keyFilename + '.pub')
        except(OSError):
            pass
        dir = os.path.dirname(keyFilename)
        if not os.path.exists(dir):
           os.makedirs(dir)
        sshCmd = 'ssh-keygen -f %s -N "" -q' % keyFilename
        self._execute([sshCmd,], quiet=False, shell=True)    

    def printAndFlush(self, msg):
        sys.stdout.flush()
        print msg,
        sys.stdout.flush()
        
    def printAction(self, msg):
        self.printAndFlush('\n :::%s:::\n' % (':' *len(msg)))
        self.printAndFlush(' :: %s ::\n' % msg)
        self.printAndFlush(' :::%s:::\n' % (':' *len(msg)))

    def printStep(self, msg):
        self.printAndFlush(' :: %s\n' % msg)
        
    def printCmd(self, msg):
        self.printAndFlush('  [Executing] %s\n' % msg)

    def stratusRunInstance(self, image, persistentDisk=None):
        cmd = ["stratus-run-instance", "--quiet", "--key", self.sshKeyPub, self.image]
        if persistentDisk:
            cmd.extend(["--persistent-disk", persistentDisk ])
        return self._execute(cmd)

    def stratusDescribeInstance(self, vmId):
        return self._execute(["stratus-describe-instance", str(vmId)])
    
    def stratusKillInstance(self, vmId):
        if vmId:
            self._execute(["stratus-kill-instance", str(vmId)])
        
    def getVmState(self, vmId):
        stateLessThanHundred = self.stratusDescribeInstance(vmId).split('\n')[1].split(' ')[2]
        stateMoreThanHundred = self.stratusDescribeInstance(vmId).split('\n')[1].split(' ')[1]
        return stateLessThanHundred or stateMoreThanHundred

    def waitVmRunningOrTimeout(self, vmId):
        start = time.time()
        self.printStep('Started waiting for VM to be up at: %s' % start)
        state = ''
        while state != 'Running' and ((time.time() - start) < self.VM_STATUS_TIMEOUT):
            state = self.getVmState(vmId)
            print "\tStatus of VM '%s' is  '%s'" % (vmId, state)
            if state == 'Failed':
                break
            time.sleep(5)
        return state  

    def stratusBuildMetadata(self, image):
        self._execute(["stratus-build-metadata", "--author=Mohammed Airaj",
                        "--os=ttylinux", "--os-version=9.3", "--os-arch=i686",
                        "--version=1.0", image])  


    def stratusSignMetadata(self, p12cert, p12passwd, image):
        self._execute(["stratus-sign-metadata", "--p12-cert=%s" % p12cert,
                        "--p12-password=%s" % p12passwd, image]) 

    def stratusValidateMetadata(self, metadata):
        self._execute(["stratus-validate-metadata", metadata])

    def stratusUploadMetadata(self, marketplace, image):
        return self._execute(["stratus-upload-metadata", "--marketplace-endpoint=%s" 
                               % marketplace, image]) 

    def getImageMetadata(self, marketplaceq, query):
        return self._execute(["curl", marketplaceq, "--get", "--data-urlencode", query])  

    def getMetadatUrlfromSparql(self, marketplace, sparql):
        xmltree = etree.fromstring(sparql)
        sparql_elems = xmltree.findall('{http://www.w3.org/2005/sparql-results#}results/{http://www.w3.org/2005/sparql-results#}result/{http://www.w3.org/2005/sparql-results#}binding')
        for elem in sparql_elems:
            if elem.get('name') == "email":
               email = elem.findtext('{http://www.w3.org/2005/sparql-results#}literal')
            elif elem.get('name') == "created":
                 created = elem.findtext('{http://www.w3.org/2005/sparql-results#}literal')
            elif elem.get('name') == "identifier":
                 identifier = elem.findtext('{http://www.w3.org/2005/sparql-results#}literal')
        metadataUrl = marketplace + "/" + identifier + "/" + email + "/" + created            
        return metadataUrl

    def stratusCreateVolume(self, tag='test-disk', size=1):
        return self._execute(["stratus-create-volume", "--size=%s" % size, "--tag=%s" % tag]) 
    
    def createPersistentDiskAndGetUUID(self, tag='tester-mydisk', size=1):
        return self.stratusCreateVolume(tag, size).split(" ")[1].replace('\n', '')
        
    def stratusDeleteVolume(self, uuid):
        self._execute(["stratus-delete-volume", uuid])    

    def stratusDescribeVolumes(self, uuid=None):
        cmd = ["stratus-describe-volumes", ]
        if uuid:
            cmd.append(uuid)
        self._execute(cmd)

    def testClaudia(self, stratus_command, claudia_test, claudia_customer, claudia_service, claudia_ovf):
        self._execute([stratus_command, claudia_test, "--claudia-customer",
                        claudia_customer, "--claudia-service", claudia_service,
                        "--claudia-ovf-endpoint", claudia_ovf])
        
    def getMetadataEntries(self, metadata):
        xmltree = etree.parse(metadata)    
        return xmltree.findtext('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description/{http://purl.org/dc/terms/}identifier')
    
    def getMarketplaceQuery(self, manifestUrl):
        manifest = etree.fromstring(self._readRemoteFile(manifestUrl))
        xpathPrefix = './/{http://mp.stratuslab.eu/slreq#}%s/{http://purl.org/dc/terms/}'
        created = manifest.findtext(xpathPrefix % 'endorsement' + 'created')
        query = ("query=PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX slreq: " +
                "<http://mp.stratuslab.eu/slreq#> select distinct ?identifier ?email" +
                " ?created where  { ?x dcterms:identifier ?identifier; slreq:endorsement" +
                " ?endorsement . ?endorsement slreq:endorser ?endorser; dcterms:created " +
                "?created .?endorser slreq:email ?email . FILTER (?created = '%s' )}" % created)
        return query

    def run(self):
        
        ##########
        self.printAction("Defined attributes")
        ##########
        
        self.printAttributes()
        
        ##########
        self.printAction("Generating a SSH key pair")
        ##########
        
        self.generateSshKeyPair(self.sshKey)
        
        ##########
        self.printAction("Virtual Machine life-cycle")
        ##########
        
        self.printStep("Running a VM")
        vm_id_ip = self.stratusRunInstance(self.image)
        
        self.vmId, vm_ip = vm_id_ip.split(', ')    
    
        self.printStep("Waiting for VM to be up")
        self.waitVmRunningOrTimeout(self.vmId)
           
        self.printStep("Killing VM")
        self.stratusKillInstance(self.vmId)
        
        ##########
        self.printAction("Image creation")
        ##########
        
        self.generateDummyImage(self.fakeImage)
        self.stratusBuildMetadata(self.fakeImage)
        self.stratusSignMetadata(self.p12Certificate, self.p12Password, self.fakeMetadata)
        self.stratusValidateMetadata(self.fakeMetadata)
        
        ###########
        self.printAction("Market place registration")
        ##########
        
        marketplace_metadata = self.marketplace + "metadata"
        imgMarketPlaceUri = self.stratusUploadMetadata(marketplace_metadata, self.fakeMetadata)
        imgUuid = self.getMetadataEntries(self.fakeMetadata)
        print "\nImage UUID: %s" % imgUuid
        
        query = self.getMarketplaceQuery(imgMarketPlaceUri)
        marketplace_query_url = self.marketplace + "query"
        imgMetadata = self.getImageMetadata(marketplace_query_url, query)     
        metadataUri = self.getMetadatUrlfromSparql(marketplace_metadata, imgMetadata)
        print '\nMetadata URI=%s' % metadataUri
        
        self.printStep("Testing new image")
        vm_id_ip = self.stratusRunInstance(metadataUri)
        
        self.vmId, vm_ip = vm_id_ip.split(', ')    
    
        self.printStep("Waiting for VM to be up")
        self.waitVmRunningOrTimeout(self.vmId)
           
        self.printStep("Killing VM")
        self.stratusKillInstance(self.vmId)
         
        #########
        self.printAction("Persistent disk storage test")
        #########
        
        self.printStep("Creating persistent disk")
        uuid = self.createPersistentDiskAndGetUUID()
        self.stratusDescribeVolumes(uuid)
        
        self.printStep("Using persistent disk")
        vm_id_ip = self.stratusRunInstance(self.image, uuid)
        
        self.vmId, vm_ip = vm_id_ip.split(', ')    
    
        self.printStep("Waiting for VM to be up")
        self.waitVmRunningOrTimeout(self.vmId)
           
        self.printStep("Killing VM")
        self.stratusKillInstance(self.vmId)
        time.sleep(5)
        
        self.printStep("Removing persistent disk")
        uuid = self.stratusDeleteVolume(uuid)
        self.stratusDescribeVolumes(uuid)
    
        ##########
        #self.printAction("Claudia test")
        #########

        #self.printStep("Executing claudia unit-test")
        #self.testClaudia("stratus-test", "claudiaTest", "demo", "ds1", self.claudiaOvfEndpoint)


if __name__ == "__main__":
    tutorial = Tutorial()
    try:
        tutorial.run()
    except Exception, e:
        print '### ABORTING ON ERROR ###'
        print e
        tutorial.stratusKillInstance(tutorial.vmId)
        sys.exit(1)
    

