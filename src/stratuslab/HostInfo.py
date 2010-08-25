from Util import assignAttributes

class HostInfo(object):
    def populateHosts(self, host):
        attribs = {}
        [attribs.__setitem__(node.tag.lower(),node.text) for node in host.getchildren()]
        assignAttributes(self,attribs)
