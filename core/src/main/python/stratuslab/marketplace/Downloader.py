import os
import shutil
import tempfile
import urllib2
import hashlib
from stratuslab.Exceptions import ExecutionException
from stratuslab.ManifestInfo import ManifestInfo

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

from stratuslab import Util
from stratuslab.Signator import Signator
from stratuslab.Compressor import Compressor
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import InputException
from stratuslab.Exceptions import ValidationException

class Downloader(object):

    ENDPOINT = 'http://appliances.stratuslab.eu/marketplace/metadata'
    LOCAL_IMAGE_FILENAME = '/tmp/image.img'

    def __init__(self, configHolder = ConfigHolder()):
        self.localImageFilename = None
        self.configHolder = configHolder
        self.imageUrl = None
        configHolder.assign(self)
        self.compression = None
        self.localImageFilename = os.path.abspath(self.localImageFilename)
    
    def download(self, uri):

        endpoint = Util.constructEndPoint(self.endpoint, 'http', '80', 'images')
        url = endpoint + '/' + uri
        tempMetadataFilename = tempfile.mktemp()
        try:
            self._download(url, tempMetadataFilename)
        except urllib2.HTTPError:
            raise InputException('Failed to find metadata entry: %s' % url)

        manifestInfo = ManifestInfo(tempMetadataFilename)

        locations = [manifestInfo.location]

        tempImageFilename = ''
        for location in locations:
            self._printDetail('Looking for image: %s' % location)
            try:
                tempImageFilename = self._downloadImage(location)
                break
            except:
                pass

        if not os.path.exists(tempImageFilename):
            raise InputException('Failed to find image matching metadata: %s' % url)

        self._verifySignature(tempImageFilename, tempMetadataFilename)

        tempImageFilename = self._inflateImage(tempImageFilename)

        self._verifyHash(tempImageFilename, manifestInfo.sha1)

        shutil.copy2(tempImageFilename, self.localImageFilename)

        os.remove(tempImageFilename)
        os.remove(tempMetadataFilename)
        
        return self.localImageFilename

    def _loadDom(self, filename):
        file = open(filename).read()
        dom = etree.fromstring(file)
        return dom

    def _downloadImage(self, url):
        compressionExtension = self._extractCompressionExtension(url)
        
        localFilename = tempfile.mktemp()
        localImageName = localFilename + compressionExtension
        
        Util.wget(url, localImageName)
        
        return localImageName

    def _extractCompressionExtension(self, url):
        compression = url.split('.')[-1]
        
        if compression in ('gz', 'bz2'):
            return '.' + compression
        else:
            return ''

    def _download(self, url, localFilename):
        try:
            return Util.wget(url, localFilename)
        except urllib2.URLError, ex:
            raise InputException('Failed to download: %s, with detail: %s' % (url, str(ex)))

    def _verifySignature(self, imageFilename, metadataFilename):
        signator = Signator(metadataFilename, self.configHolder)
        res = signator.validate()
        if res:
            raise ExecutionException('Failed to validate metadata file')

    def _inflateImage(self, imageFilename):
        extension = self._extractCompressionExtension(imageFilename)
        inflatedFilename = imageFilename
        if extension:
            self._printDetail('Inflating image %s' % imageFilename)
            Compressor.inflate(imageFilename)
            inflatedFilename = imageFilename[: - len(extension)]
        
        return inflatedFilename
    
    def _verifyHash(self, imageFilename, hashFromManifest):

        data = open(imageFilename).read()
        sha1 = hashlib.sha1()
        sha1.update(data)
        
        imageHash = sha1.hexdigest()
        
        if imageHash != hashFromManifest:
            raise ValidationException('Manifest hash code different from downloaded image: image=%s, matadata=%s' % (imageHash, hashFromManifest))

    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, 1)
        
