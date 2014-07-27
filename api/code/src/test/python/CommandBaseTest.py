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
import unittest
import os
import sys

from stratuslab.commandbase.CommandBase import CommandBaseUser
from optparse import OptionParser

import stratuslab.Util as Util
import stratuslab.Exceptions as Exceptions

class helperClass(object):
    pass

fooBarDefault = 'foo'
attrDest = 'fooBar'
confParam = 'foo_bar'

class CommandBaseUserTestor(CommandBaseUser):
    def __init__(self, args=[], config={}):

        self.parser = OptionParser()
        self.parser.add_option('--foo-bar', dest=attrDest,
                default=fooBarDefault)

        self.options, _ = self.parser.parse_args(args)

        self.config = config
        
        self._configKeysClassAttrsTwoWayMap = {attrDest:confParam,
                                               confParam:attrDest}

class CommandBaseUserTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testUseDefaultValue(self):
        try:
            cb = CommandBaseUserTestor()
            cb._loadConfigFileAndUpdateOptions()
        except Exception, ex:
            self.fail(str(ex))

        assert getattr(cb.options, attrDest) == fooBarDefault

    def testUseConfFileValue(self):
        cb = CommandBaseUserTestor(args=[],
                                   config={attrDest:'abc'})
        cb._updateOptionsFromConfigFile()
        assert cb.options.fooBar != fooBarDefault
        assert cb.options.fooBar == 'abc'
    
    def testUseEnvVarValue(self):
        envVar = 'STRATUSLAB_%s' % confParam.upper()
        os.environ[envVar] = 'cde'
        sys.argv = ['xyz','XYZ']
        
        cb = CommandBaseUserTestor(args=[],
                                   config={attrDest:'abc'})
        setattr(cb.options, attrDest, os.environ[envVar])
        cb._updateOptionsFromConfigFile()

        assert getattr(cb.options, attrDest) != fooBarDefault
        assert getattr(cb.options, attrDest) == 'cde'
    
        os.unsetenv(envVar)
    
    def testUseCliValue(self):
        cb = CommandBaseUserTestor(args=['--foo-bar','foo'])
        cb._updateOptionsFromConfigFile()
        assert getattr(cb.options, attrDest) == 'foo'
        
if __name__ == "__main__":
    unittest.main()
