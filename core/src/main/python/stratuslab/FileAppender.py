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
import os
import shutil

class FileAppender(object):
    
    def __init__(self, filename):
        self.filename = filename
        self.lines = []
        self.newLines = []
        self.foundExit = False
    
    def insertAtTheEnd(self, newLine):
        ''' Append at the end of the file (e.g. rc.local) the newLine
            at the end of the file, unless the file ends with 'exit',
            in which case it inserts just before.'''
        
        self._backupIfNecessary()
        
        self._reverseLines()

        newLine = newLine + '\n' 
        
        self.foundExit = False
        for line in self.lines:
            if line.strip() == '':
                self._appendNewLine(line)
                continue
            if self._containsExit(line):
                self._insertLines(line, newLine)
                continue
            if self.foundExit:
                self._appendNewLine(line)
                continue
            self._insertLines(newLine, line)
        
        self.newLines.reverse()
        
        self._writeAndClose()
    
    def _backupIfNecessary(self):
        originalFilename = self.filename + '.orig'
        if not os.path.exists(originalFilename):
            shutil.copyfile(self.filename, originalFilename)
    
    def _reverseLines(self):
        file = open(self.filename)
        self.lines = file.readlines()
        self.lines.reverse()
    
    def _appendNewLine(self, line):
        self.newLines.append(line)
    
    def _containsExit(self, line):
        return line.strip().startswith('exit')
    
    def _insertLines(self, first, second):
        self.foundExit = True
        self._appendNewLine(first)
        self._appendNewLine(second)
    
    def _writeAndClose(self):
        newfile = open(self.filename, 'w')
        newfile.writelines(self.newLines)
        newfile.close()
        os.chmod(self.filename, 0755)
