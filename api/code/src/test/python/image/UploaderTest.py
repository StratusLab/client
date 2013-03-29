import unittest

from mock.mock import Mock
from stratuslab.image.Uploader import Uploader
from stratuslab.ConfigHolder import ConfigHolder

class UploaderTest(unittest.TestCase):

    def setUp(self):
        self._uploadVolume = Mock(return_value='https://example.com/pdisk/uuid')
        self._updateVolumeAsUser = Mock()

        self.ch = ConfigHolder()
        self.ch.set('pdiskEndpoint', 'example.com')

    def tearDown(self):
        pass

    def test_uploadImageNoVolumeUpdate(self):

        uploader = Uploader('image.img', self.ch)
        uploader.pdisk.uploadVolume = self._uploadVolume
        uploader.pdisk.updateVolumeAsUser = self._updateVolumeAsUser
        uploader._uploadImage()

        assert uploader.pdisk.uploadVolume.called == True
        assert uploader.pdisk.uploadVolume.call_count == 1
        assert uploader.pdisk.uploadVolume.call_args == (('image.img',), {})
        assert uploader.pdisk.uploadVolume._return_value == 'https://example.com/pdisk/uuid'

        assert uploader.pdisk.updateVolumeAsUser.called == False

    def test_uploadImageVolumeUpdate(self):
        self.ch.set('imageMetadata', {'foo':'bar'})

        uploader = Uploader('image.img', self.ch)
        uploader.pdisk.uploadVolume = self._uploadVolume
        uploader.pdisk.updateVolumeAsUser = self._updateVolumeAsUser
        uploader._uploadImage()

        assert uploader.pdisk.uploadVolume.called == True
        assert uploader.pdisk.uploadVolume.call_count == 1
        assert uploader.pdisk.uploadVolume.call_args == (('image.img',), {})
        assert uploader.pdisk.uploadVolume._return_value == 'https://example.com/pdisk/uuid'

        assert uploader.pdisk.updateVolumeAsUser.called == True
        assert uploader.pdisk.updateVolumeAsUser.call_count == 1
        assert uploader.pdisk.updateVolumeAsUser.call_args == (({'foo':'bar'}, 'uuid'), {})

if __name__ == "__main__":
    unittest.main()
