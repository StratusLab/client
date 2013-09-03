#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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

import logging as log
import ConfigParser
from couchbase import Couchbase

class stratuslab.dbutils.CouchbaseHandler (log.Handler):
    """
    Provides a logging handler that inserts records into a Couchbase
    database.  The log records are formatted according to the
    configured formatter and appended to the given Couchbase document
    directly.

    Exceptions raised while constructing the handler will be passed on
    to the caller.  Exceptions raised while logging will be treated
    with the installed error handler, which by default, ignores such
    errors. 
    """

    def _create_docid(self):
        """
        Add the given document to the database.  Exceptions raised
        while trying to create the document will be ignored; this may
        happen if the document exists already.
        """
        try:
            self.cb.add(self.docid,'')
        except:
            pass

    def __init__(self, docid, dbhost='127.0.0.1', 
                 bucket='default', password='', level=log.INFO):
        """
        Constructor requires the document ID (docid) for the log.
        This will usually be related to the VM (or other resource)
        being logged.

        The log level (default = logger.INFO) is optional.

        The following additional keyword arguments are accepted:
          * dbhost = host:port for server (def. '127.0.0.1:8091')
          * bucket = name of bucket to use (def. 'default')
          * password = password for bucket (def. '')
        """
        super(CouchbaseHandler, self).__init__(level=level)

        self.cb = Couchbase.connect(host=dbhost, bucket=bucket, password=password)

        if not docid:
            raise Exception('docid cannot be empty or null')

        self.docid = docid

        self._create_docid()

    def emit(self, record):
        """
        Simply append the given record to the document within the
        database.
        """
        try:
            msg = self.format(record) + "\n"
            self.cb.append(self.docid, msg)
        except:
            self.handleError(record)
