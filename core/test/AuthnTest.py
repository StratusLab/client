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
from stratuslab.Authn import UsernamePasswordCredentialsLoader,\
    SimpleConfigParser
from StringIO import StringIO

class SimpleConfigParserTest(unittest.TestCase):

    def test_username_password_loader(self):
        filecontent = '''# Entries look like the following:
#
# username=password,cloud-access
#
# 'cloud-access' is a required role
# 

username=password,group
username_with_multiple_values=password, group1, group2
'''
        loader = UsernamePasswordCredentialsLoader()
        test_file = StringIO()
        test_file.write(filecontent)
        test_file.seek(0)
        loader.load(test_file)
        self.assertEqual(('password','group'), loader.get('username'))
        self.assertEqual('password', loader.get_password('username'))
        self.assertEqual('group', loader.get_group('username'))        
        self.assertEqual('group1, group2', loader.get_group('username_with_multiple_values'))

    def test_invalid_line(self):
        filecontent = '''# Entries look like the following:
#
# username=password,cloud-access
#
# 'cloud-access' is a required role
# 

missing_equal_and_value
'''
        loader = SimpleConfigParser()
        test_file = StringIO()
        test_file.write(filecontent)
        test_file.seek(0)
        self.assertRaises(ValueError, loader.load, test_file)
                
if __name__ == "__main__":
    unittest.main()
