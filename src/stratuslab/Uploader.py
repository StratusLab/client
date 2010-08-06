from stratuslab.Util import execute
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep

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
                

class Uploader(object):

    def __init__(self, config, manifest, options):
        self.config = config
        self.manifest = manifest
        self.username = options.username
        self.password = options.password
        self.uploadOption = options.option
        self.protocol = options.uploadProtocol
        self.repo = options.repoAddress

        # Attribute initialization
        self.system = None
        self.version = None
        self.category = None
        self.architecture = None
        self.uploadCmd = None

    def _parseManifest(self):
        xml = etree.ElementTree()
        xml.parse(self.manifest)
        self.system = xml.find('system').text
        self.version = xml.find('version').text
        self.architecture = xml.find('architecture').text
        self.category = xml.find('category').text

    def _uploadFile(self, filename):
        # See in the future for additional methods
        self._curlUpload(filename)

    def _curlUpload(self, filename):
        repoTree = self.config.get('app_repo_tree')
        for part in ('category', 'system', 'architecture', 'version'):
            if repoTree.find(part) != -1:
                repoTree = repoTree.replace('#%s#' % part, getattr(self, part, ''))

        repoUrl = '%s://%s/%s' % (self.protocol, self.repo, repoTree)

        curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.username,
                                                        self.password)]

        # We have to create in a first time the directories before uploading
        # the appliance and his manifest.
        newDirs = self._listRecursiveUrlDirs(repoUrl)
        self._curlCreateRecursiveDirs(newDirs, curlCmd)

        curlUploadCmd = curlCmd + ['-T', filename]

        if self.uploadOption:
            curlUploadCmd.append(repoUrl)
            
        curlUploadCmd.append(repoUrl)
        devNull = open('/dev/null', 'w')
        ret = execute(*curlUploadCmd, stdout=devNull, stderr=devNull)
        devNull.close()
        
        if ret != 0:
            printError('An error occured while uploading %s' % filename)

#        passwordMgr =  urllib2.HTTPPasswordMgrWithDefaultRealm()
#        passwordMgr.add_password(None, '%s://%s' % (self.protocol, self.repo),
#                                 self.password, self.username)
#        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
#        opener = urllib2.build_opener(handler)
#
#        file = open(filename, 'r+')
#        size = os.path.getsize(filename)
#        data = mmap.mmap(file.fileno(), size)
#
#        request = urllib2.Request(repoUrl, data=data)
#        request.add_header('Content-Type', 'application/octet-stream')
#        request.get_method = lambda: 'PUT'
#
#        opener.open(request)
#        urllib2.install_opener(opener)

    def _listRecursiveUrlDirs(self, url):
        urlDirs = '/'.join(url.split('//')[1:])
        newDirs = ['']
        for dir in urlDirs.split('/')[1:]:
            newDirs.append('%s/%s' % (newDirs[-1], dir))

        return newDirs[1:]

    def _curlCreateRecursiveDirs(self, dirs, curlBaseCmd):
        devNull = open('/dev/null', 'w')
        curlCreateDirCmd = curlBaseCmd + ['-X', 'MKCOL']

        for dir in dirs:
            curlCreateDirCmd.append('%s://%s%s/' % (self.protocol,
                                                   # Find root address of the repo
                                                   self.repo.split('/')[0],
                                                   dir))
            execute(*curlCreateDirCmd, stderr=devNull, stdout=devNull)
            curlCreateDirCmd.pop()
        devNull.close()

    @staticmethod
    def availableProtocol():
        return ('http', 'https')

    def start(self):
        printAction('Starting appliance upload')

        printStep('Parsing manifest')
        self._parseManifest()

        printStep('Uploading appliance')
        self._uploadFile(self.manifest.replace('.manifest.xml', ''))

        printStep('Uploading manifest')
        self._uploadFile(self.manifest)

        printAction('Upload finished successfuly')