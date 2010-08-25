
import unittest

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

from stratuslab.CloudInfo import CloudInfo

class VmInfoTest(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testPopulate(self):
        xml = '''
<root>
    <level1>
        <id1>ID1</id1>
        <level2>
            <level3>
                <id3>ID3</id3>
            </level3>
        </level2>
    </level1>
</root>
'''
        root = etree.fromstring(xml)

        info = CloudInfo()
        info.populate(root)
        
        self.assertEqual('ID1',info.id1)
        self.assertEqual('ID3',info.id3)

if __name__ == "__main__":
    unittest.main()