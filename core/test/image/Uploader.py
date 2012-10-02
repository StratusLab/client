import unittest

from mock.mock import Mock
from stratuslab.image.Uploader import Uploader
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.PersistentDisk import PersistentDisk

class UploaderTest(unittest.TestCase):

    def setUp(self):
        PersistentDisk.__init__ = Mock(return_value=None)
        PersistentDisk.uploadVolume = Mock(return_value='https://example.com/pdisk/uuid')
        PersistentDisk.updateVolumeAsUser = Mock()

    def tearDown(self):
        pass

    def test_uploadImageNoVolumeUpdate(self):

        uploader = Uploader('image.img', ConfigHolder())
        uploader._uploadImage()
        assert PersistentDisk.uploadVolume.called == True
        assert PersistentDisk.uploadVolume.call_count == 1
        assert PersistentDisk.uploadVolume.call_args == (('image.img',), {})
        assert PersistentDisk.uploadVolume._return_value == 'https://example.com/pdisk/uuid'

        assert PersistentDisk.updateVolumeAsUser.called == False

    def test_uploadImageVolumeUpdate(self):

        ch = ConfigHolder()
        ch.set('imageMetadata', {'foo':'bar'})

        uploader = Uploader('image.img', ch)
        uploader._uploadImage()

        assert PersistentDisk.uploadVolume.called == True
        assert PersistentDisk.uploadVolume.call_count == 1
        assert PersistentDisk.uploadVolume.call_args == (('image.img',), {})
        assert PersistentDisk.uploadVolume._return_value == 'https://example.com/pdisk/uuid'

        assert PersistentDisk.updateVolumeAsUser.called == True
        assert PersistentDisk.updateVolumeAsUser.call_count == 1
        assert PersistentDisk.updateVolumeAsUser.call_args == (({'foo':'bar'}, 'uuid'), {})

if __name__ == "__main__":
    unittest.main()
