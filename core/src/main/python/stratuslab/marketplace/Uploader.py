
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.HttpClient import HttpClient
from stratuslab.Exceptions import InputException
import os
from stratuslab.ManifestInfo import ManifestInfo

class Uploader(object):

    def __init__(self, configHolder = ConfigHolder()):
        self.confHolder = configHolder
        configHolder.assign(self)

    def upload(self, manifestFilename):
        client = HttpClient()
        if not os.path.exists(manifestFilename):
            raise InputException('Can\'t find metadata file: %s' % manifestFilename)
        
        manifest = open(manifestFilename).read()

        info = ManifestInfo(self.confHolder)
        info.parseManifest(manifest)
        
        url = self.marketPlaceEndpoint + '/' + info.identifier
        client.post(url, manifest)
