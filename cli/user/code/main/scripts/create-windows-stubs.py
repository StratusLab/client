#!/usr/bin/env python

import os
import stat
import glob
import StringIO

input_path='main/python/'
output_path='target/windows/'

stub='@echo off\r\npython "%~dp0\\%~n0" %*\r\n'

def process_file(file):
    output_basename = os.path.basename(file)
    output_name = output_basename + ".bat"
    output_file = os.path.join(output_path, output_name)
    print output_basename + " --> " + output_file
    f = open(output_file, "w")
    f.write(stub)
    f.close()
    os.chmod(output_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |  
             stat.S_IRGRP | stat.S_IXGRP | 
             stat.S_IROTH | stat.S_IXOTH)

try:
    os.makedirs(output_path)
except OSError as e:
    print "Ignoring directory create error.  Directory may exist."
    print e

for file in glob.glob(os.path.join(input_path, 'stratus-*')):
    process_file(file)
