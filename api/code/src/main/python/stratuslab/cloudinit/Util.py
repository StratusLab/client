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

"""
The maximum number of bytes that can be passed as user data is
limited (essentially by AWS).  Having such a limit avoids DOS
attacks; enforce the limit here.
"""
MAX_BYTES = 16384


def _strip_args(args):
    """
    Strips white space from the ends of each argument and
    removes any empty strings from the list of arguments.
    """
    return filter(None, [a.strip() for a in args])


def _mimetype_tuple(mimetype_pair):
    """
    Splits the mimetype pair on commas and returns a tuple
    with the first two values.  The returned values have whitespace
    stripped from both ends.
    """
    try:
        mimetype, filename = mimetype_pair.split(',')
        return mimetype.strip(), filename.strip()
    except ValueError:
        raise Exception("invalid CloudInit mimetype pair: '%s'" % mimetype_pair)


def _mimetype_tuples(args):
    """
    Converts the list of CloudInit mimetype pairs into a list
    of two-element tuples (mimetype and filename).  Empty values
    are ignored.
    """
    return [_mimetype_tuple(a) for a in _strip_args(args)]


def create_multipart_string(parts):
    """
    This creates a single multipart file from the given parts.  Each part
    must be a tuple containing mime-type and the raw contents.  The
    mime-type should be the subtype ONLY.  All files are assumed to be
    text files.
    """

    msg = MIMEMultipart()
    index = 0
    for mimetype, content in parts:
        part = create_text_part(content, mimetype, ('part-%s' % index))
        index += 1
        msg.attach(part)
        if mimetype == 'none':
            return content

    return msg.as_string()


def create_multipart_string_from_files(parts):
    """
    This creates a single multipart file from the given parts.  Each part
    must be a tuple containing mime-type and the file to include.  The
    mime-type should be the subtype ONLY.  All files are assumed to be
    text files.
    """
    msg = MIMEMultipart()
    for mimetype, filename in parts:
        with open(filename, 'rb') as f:
            contents = f.read()
            part = create_text_part(contents, mimetype, os.path.basename(filename))
            msg.attach(part)
            if mimetype == 'none':
                return contents

    return msg.as_string()


def create_text_part(content, mimetype, filename):
    """
    Create a text message part with the given content, mimetype, and
    filename.
    """

    part = MIMEText(content, mimetype)
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    return part


def encode_multipart(multipart):
    """
    This gzips the multipart content and then base64 encodes the result.
    The result is compatible with sending as a value in the context
    key-value pairs supported by OpenNebula.  Note that this checks that
    the maximum size of the result does not exceed 16384 bytes.
    """

    with closing(StringIO()) as buf:
        with closing(GzipFile('', 'wb', 9, buf)) as f:
            f.write(multipart)
        gzipped_data = buf.getvalue()

    gzipped_size = len(gzipped_data)
    if gzipped_size > MAX_BYTES:
        raise ValueError(SIZE_ERROR_MSG % (gzipped_size, MAX_BYTES))

    return base64.b64encode(gzipped_data)


def decode_multipart(encoded_multipart):
    """
    Decodes the multipart content and returns it.  The input must be
    a base64 encoded, gzipped file.  It will only decode values that
    do not exceed the maximum size.
    """
    gzipped_data = base64.b64decode(encoded_multipart)
    gzipped_size = len(gzipped_data)
    if gzipped_size > MAX_BYTES:
        raise ValueError(SIZE_ERROR_MSG % (gzipped_size, MAX_BYTES))

    with closing(StringIO(gzipped_data)) as buf:
        with closing(GzipFile('', 'rb', 9, buf)) as f:
            return f.read()


def decode_multipart_as_json(dsmode, encoded_multipart):
    """
    Decodes the multipart content and returns it as JSON.
    """

    info = {}
    if encoded_multipart:
        info['user-data'] = decode_multipart(encoded_multipart)
    info['dsmode'] = dsmode

    return json.dumps(info)


def create_authorized_keys_from_files(keyfiles):
    """
    Creates an authorized_keys file from the given key file(s).  The
    result has one key per line (assuming that the input in on one
    line.
    """

    with closing(StringIO()) as buf:
        for keyfile in keyfiles:
            with open(keyfile, 'r') as f:
                lines = []
                for line in f:
                    line = line.strip()
                    if not line.startswith('Comment:'):
                        lines.append(line)
                buf.write("\n".join(lines))
            buf.write("\n")
        return buf.getvalue()


def encoded_user_data(args):
    """
    Creates the encoded contents for the user data given a list of
    arguments.  Each argument must be a mimetype and filename pair
    separated by a comma.  This treats all of the mimetypes except the
    pseudo-mimetype of 'ssh'.
    """

    mimefiles = []
    for mimetype, filename in _mimetype_tuples(args):
        if mimetype != 'ssh':
            mimefiles.append((mimetype, filename))

    if len(mimefiles) == 0:
        return None
    else:
        return encode_multipart(create_multipart_string_from_files(mimefiles))


def encoded_authorized_keys_file(args, default_public_key_file=None):
    """
    Create the encoded contents for the authorized key file from the given
    list of arguments.  Each argument must be a mimetype and filename pair
    separated by a comma.  This ignores all entries except those with the
    pseudo-mimetype of 'ssh'.
    """

    keyfiles = []

    for mimetype, filename in _mimetype_tuples(args):
        if mimetype == 'ssh':
            keyfiles.append(filename)

    if len(keyfiles) == 0 and (default_public_key_file is not None):
        keyfiles.append(default_public_key_file)

    if len(keyfiles) == 0:
        return None
    else:
        contents = create_authorized_keys_from_files(keyfiles)
        return base64.b64encode(contents)


def context_file(args, separator="\n", default_public_key_file=None):
    """
    Creates the contents of the context file with the given list of
    arguments.  The method accepts an optional separator character, which
    is a newline by default. Each argument must be a mimetype and filename
    pair separated by a comma.
    """

    authorized_keys = encoded_authorized_keys_file(args, default_public_key_file=default_public_key_file)
    user_data = encoded_user_data(args)

    # Do NOT add spaces around the equals sign.  These will leak into the
    # values defined in the context file defined by OpenNebula.
    kvpairs = ['CONTEXT_METHOD=cloud-init']
    if authorized_keys:
        kvpairs.append("CLOUD_INIT_AUTHORIZED_KEYS=%s" % authorized_keys)
    if user_data:
        kvpairs.append("CLOUD_INIT_USER_DATA=%s\n" % user_data)

    return separator.join(kvpairs)
