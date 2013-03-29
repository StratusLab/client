#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from Util import assignAttributes

class CloudInfo(object):
    
    def __init__(self):
        self.attribs = {}
        
    def populate(self, element):
        self._populate(element)
        assignAttributes(self, self.attribs)

    def _populate(self, element, parentHierachy=[]):
        children = self._getChildren(element)
        if children:
            _parentHierachy = self._updateHierachy(element, parentHierachy)
            for child in children:
                self._populate(child, _parentHierachy)
        else:
            # skip the root element
            hierachy = parentHierachy[1:] + [element.tag]
            attributeName = '_'.join(hierachy)
            if isinstance(element.text, unicode):
                text = element.text.encode('utf-8')
            else:
                text = element.text
            self.attribs.__setitem__(attributeName.lower(), text)
        return

    def _getChildren(self, parent):
        return parent.getchildren()
    
    def _updateHierachy(self, element, parentHierachy):
        _parentHierachy = parentHierachy[:]
        _parentHierachy.append(element.tag)
        return _parentHierachy

    def getAttributes(self):
        return self.attribs

    def set(self, key, value):
        setattr(self, key, value)
