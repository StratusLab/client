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
        self.manifestExt = '.manifest.xml'
        
        self.curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.username,
                                                             self.password)]

        # Attribute initialization
        self.system = None
        self.version = None
        self.category = None
        self.architecture = None
        self.uploadCmd = None
        self.uploadUrl = None

    def _parseManifest(self):
        xml = etree.ElementTree()
        xml.parse(self.manifest)
        self.os = xml.find('os').text
        self.osversion = xml.find('osversion').text
        self.arch = xml.find('arch').text
        self.type = xml.find('type').text
        self.version = xml.find('version').text

    def _uploadFile(self, filename, manifest=False):
        # See in the future for additional methods
        self._curlUpload(filename, manifest)

    def _curlUpload(self, filename, manifest):
        imageDirectory = self._parseRepoStructure(self.config.get('app_repo_tree'))
        imageName = self._parseRepoStructure(self.config.get('app_repo_filename'))

        repoUrl = '%s://%s/%s' % (self.protocol, self.repo, imageDirectory)
        extension = manifest and self.manifestExt or ''

        self.uploadUrl = '%s/%s%s' % (repoUrl, imageName, extension)

        # We have to create in a first time the directories before uploading
        # the appliance and his manifest.
        newDirs = self._listRecursiveUrlDirs(repoUrl)
        self._curlCreateRecursiveDirs(newDirs, self.curlCmd)

        curlUploadCmd = self.curlCmd + ['-T', filename]

        if self.uploadOption:
            curlUploadCmd.append(self.uploadOption)
            
        curlUploadCmd.append(self.uploadUrl)

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

    def _parseRepoStructure(self, structure):
        varPattern = '#%s#'
        dirVarPattern = '#%s_#'
        for part in ('type', 'os', 'arch', 'version', 'osversion'):
            if structure.find(varPattern % part) != -1:
                structure = structure.replace(varPattern % part, getattr(self, part, ''))

            if structure.find(dirVarPattern % part) != -1:
                structure = structure.replace(dirVarPattern % part, getattr(self, part, '').replace('.', '/'))

        return structure

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
        self._uploadFile(self.manifest.replace(self.manifestExt, ''))

        printStep('Uploading manifest')
        self._uploadFile(self.manifest, manifest=True)

        printAction('Appliance uploaded successfully')
        print '\n\t%s' % self.uploadUrl
        print '\t%s' % self.uploadUrl.replace(self.manifestExt, '')
        