import unittest

from stratuslab.Image import Image
from stratuslab.Compressor import Compressor

class ImageTest(unittest.TestCase):

    def testValidImageEndpoints(self):

        for proto in ['ftp','http','https']:

            for imgFormat in ['img', 'qco', 'qcow', 'qcow2']:
                urlImgFormat = '%s://foo:123/bar.%s' % (proto, imgFormat)
                self.failUnless(Image.re_imageUrl.match(urlImgFormat), urlImgFormat)

                for compression in Compressor.compressionFormats:
                    urlCompressed = '%s.%s' % (urlImgFormat, compression)
                    self.failUnless(Image.re_imageUrl.match(urlCompressed), urlCompressed)
    
    def testInvalidImageEndpoints(self):
        assert Image.re_imageUrl.match('') == None
        assert Image.re_imageUrl.match('a') == None
        assert Image.re_imageUrl.match('https://foo/bar.') == None
        assert Image.re_imageUrl.match('https://foo/bar.img.') == None

if __name__ == "__main__":
    unittest.main()
