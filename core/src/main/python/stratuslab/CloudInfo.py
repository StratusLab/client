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
    
