from Util import assignAttributes

class CloudInfo(object):
    
    def __init__(self):
        self.attribs = {}
        
    def populate(self, element):
        self._populate(element)
        assignAttributes(self, self.attribs)

    def _populate(self, element):
        children = self._getChildren(element)
        if children:
            for child in children:
                self._populate(child)
        else:
            self.attribs.__setitem__(element.tag.lower(),element.text)
        return

    def _getChildren(self, parent):
        return parent.getchildren()
    