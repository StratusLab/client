#
# Copyright (c) 2012, Centre National de la Recherche Scientifique (CNRS)
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
import base64
import json
import os

from gzip import GzipFile
from StringIO import StringIO

from contextlib import closing

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SIZE_ERROR_MSG = 'multipart size (%d) exceeds limit (%d)'

'''
The maximum number of bytes that can be passed as user data is
limited (essentially by AWS).  Having such a limit avoids DOS
attacks; enforce the limit here. 
'''
MAX_BYTES = 16384

'''
This creates a single multipart file from the given parts.  Each part
must be a tuple containing mime-type and the raw contents.  The 
mime-type should be the subtype ONLY.  All files are assumed to be 
text files.
'''
def createMultipartString(parts):
    msg = MIMEMultipart()
    is_multipart = (len(parts) != 1)
    index = 0
    for mimetype, content in parts:
        part = createTextPart(content, mimetype, ('part-%s' % index))
        index = index + 1
        if is_multipart: 
            msg.attach(part)
        else:
            msg = part
        
    return msg.as_string()

'''
This creates a single multipart file from the given parts.  Each part
must be a tuple containing mime-type and the file to include.  The
mime-type should be the subtype ONLY.  All files are assumed to be
text files.
'''
def createMultipartStringFromFiles(parts):
    msg = MIMEMultipart()
    is_multipart = (len(parts) != 1)
    for mimetype, file in parts:
        with open(file, 'rb') as f:
            part = createTextPart(f.read(), mimetype, os.path.basename(file))
        if is_multipart:
            msg.attach(part)
        else:
            msg = part

    return msg.as_string()


'''
Create a text message part with the given content, mimetype, and
filename.
'''
def createTextPart(content, mimetype, filename):
    part = MIMEText(content, mimetype)
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    return part


'''
This gzips the multipart content and then base64 encodes the result.
The result is compatible with sending as a value in the context 
key-value pairs supported by OpenNebula.  Note that this checks that
the maximum size of the result does not exceed 16384 bytes.
'''
def encodeMultipart(multipart):
    with closing(StringIO()) as buffer:
        with closing(GzipFile('', 'wb', 9, buffer)) as f:
            f.write(multipart)
        gzipped_data = buffer.getvalue()

    gzipped_size = len(gzipped_data)
    if (gzipped_size > MAX_BYTES):
        raise ValueError(SIZE_ERROR_MSG % (gzipped_size, MAX_BYTES))

    return base64.b64encode(gzipped_data)

'''
Decodes the multipart content and returns it.  The input must be 
a base64 encoded, gzipped file.  It will only decode values that 
do not exceed the maximum size.
'''
def decodeMultipart(encoded_multipart):
    gzipped_data = base64.b64decode(encoded_multipart)
    gzipped_size = len(gzipped_data)
    if (gzipped_size > MAX_BYTES):
        raise ValueError(SIZE_ERROR_MSG % (gzipped_size, MAX_BYTES))

    with closing(StringIO(gzipped_data)) as buffer:
        with closing(GzipFile('', 'rb', 9, buffer)) as f:
            return f.read()

'''
'''
def decodeMultipartAsJson(dsmode, encoded_multipart):
    info = {}
    info['user-data'] = decodeMultipart(encoded_multipart)
    info['dsmode'] = dsmode

    return json.dumps(info)

'''
Creates an authorized_keys file from the given key file(s).  The
result has one key per line (assuming that the input in on one
line.
'''
def createAuthorizedKeysFromFiles(keyfiles):
    with closing(StringIO()) as buffer:
        for keyfile in keyfiles:
            with open(keyfile, 'rb') as f:
                key = f.read()
                buffer.write(key.strip())
            buffer.write("\n")
        return buffer.getvalue()
