import urllib2

from stratuslab.Util import execute
from stratuslab.Util import manifestExt
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
        self.appliance = self.manifest.replace(manifestExt, '')
        self.username = options.username
        self.password = options.password
        self.uploadOption = options.option
        self.protocol = options.uploadProtocol
        self.repo = options.repoAddress
        self.compressionFormat = options.archiveFormat
        self.forceUpload = options.forceUpload
        
        self.uploadedFile = []
        
        self.curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.username,
                                                             self.password)]

        # Attribute initialization
        self.os = None
        self.osversion = None
        self.arch = None
        self.type = None
        self.version = None
        self.compresion = None

    def _parseManifest(self):
        xml = etree.ElementTree()
        xml.parse(self.manifest)
        self.os = xml.find('os').text
        self.osversion = xml.find('osversion').text
        self.arch = xml.find('arch').text
        self.type = xml.find('type').text
        self.version = xml.find('version').text
        self.compression = xml.find('compression').text

    def _uploadFile(self, filename, manifest=False):
        repoTree = self._parseRepoStructure(self.config.get('app_repo_tree'))
        repoFilename = self._parseRepoStructure(self.config.get('app_repo_filename'))
        repoUrl = '%s://%s/%s' % (self.protocol, self.repo, repoTree)
        extension = manifest and manifestExt or ''

        # Hack to don' put the compression extension to the manifest filename
        if manifest and repoFilename.endswith('.%s' % self.compressionFormat):
            repoFilename = repoFilename.replace('.%s' % self.compressionFormat, '')

        uploadUrl = '%s/%s%s' % (repoUrl, repoFilename, extension)

        self._checkExistingApplianceOnRepo(uploadUrl)
        self.uploadedFile.append(uploadUrl)

        # Create the directory tree on the repo
        newDirs = self._getDirectoriesOfUrl(repoUrl)
        self._curlCreateRecursiveDirs(newDirs, self.curlCmd)

        curlUploadCmd = self.curlCmd + ['-T', filename]

        if self.uploadOption:
            curlUploadCmd.append(self.uploadOption)
            
        curlUploadCmd.append(uploadUrl)

        devNull = open('/dev/null', 'w')
        ret = execute(*curlUploadCmd, stdout=devNull, stderr=devNull)
        devNull.close()
        
        if ret != 0:
            printError('An error occured while uploading %s' % filename)

    def _parseRepoStructure(self, structure):
        varPattern = '#%s#'
        dirVarPattern = '#%s_#'
        for part in ('type', 'os', 'arch', 'version', 'osversion', 'compression'):
            if structure.find(varPattern % part) != -1:
                structure = structure.replace(varPattern % part, getattr(self, part, ''))

            if structure.find(dirVarPattern % part) != -1:
                structure = structure.replace(dirVarPattern % part, getattr(self, part, '').replace('.', '/'))

        return structure

    def _getDirectoriesOfUrl(self, url):
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

    def _compressFile(self, archiveName, format, *files):
        fileList = ' '.join(files)

        formatLetter = ''
        if format == 'tar.gz':
            formatLetter = 'z'
        elif format == 'tar.bz2':
            formatLetter = 'j'
        elif format == 'tar.xz':
            formatLetter = 'J'

        devNull = open('/dev/null', 'w')
        execute('tar', '-c%sf' % formatLetter, archiveName, fileList,
                stderr=devNull, stdout=devNull)
        devNull.close()

    def _compressAppliance(self):
        self._compressFile('%s.%s' % (self.appliance, self.compressionFormat),
                           self.compressionFormat, self.appliance)
        self.appliance = '%s.%s' % (self.appliance, self.compressionFormat)
        self._addCompressFormatManifest()

    def _addCompressFormatManifest(self):
        compressionElem = etree.Element('compression')
        compressionElem.text = self.compressionFormat

        xml = etree.ElementTree()
        manifest = xml.parse(self.manifest)
        manifest.append(compressionElem)

        xml.write(self.manifest)

    def _checkExistingApplianceOnRepo(self, url):
        applianceRepoUrl = '%s://%s' % (self.protocol, self.repo)

        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None, applianceRepoUrl, self.username, self.password)

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        status = 0
        try:
            opener.open(url)
        except Exception, e:
            status = e.getcode()

        if status != 404 and not self.forceUpload:
            printError('An appliance already exist at this URL.\n'
                       'Change the appliance version of force upload with '
                       '-f --force option')

    @staticmethod
    def availableCompressionFormat(printIt=False):
        list = ('tar.gz', 'tar.bz2', 'tar.xz')

        if printIt:
            print 'Available compression format: %s' % ', '.join(list)
        else:
            return list

    @staticmethod
    def availableUploadProtocol(printIt=False):
        list = ('http', 'https')

        if printIt:
            print 'Available upload protocol: %s' % ', '.join(list)
        else:
            return list

    def start(self):
        printAction('Starting appliance upload')

        printStep('Compressing appliance')
        self._compressAppliance()

        printStep('Parsing manifest')
        self._parseManifest()

        printStep('Uploading appliance')
        self._uploadFile(self.appliance)

        printStep('Uploading manifest')
        self._uploadFile(self.manifest, manifest=True)

        printAction('Appliance uploaded successfully')
        print '\n\t%s' % '\n\t'.join(self.uploadedFile)
        