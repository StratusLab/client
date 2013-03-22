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
from couchbase.client import Couchbase

class stratuslab.dbutils.CouchbaseHandler (log.Handler):
"""
Provides a logging handler that inserts records into a Couchbase
database.  The log records are formatted according to the configured
formatted and appended to the given Couchbase document directly.  This
document is considered a plain text file and is not formatted as
JSON.
"""
    def __init__(self, 
                 logid='mylog', 
                 dbnode="127.0.0.1:8091",
                 bucket='default',
                 password=''):
        """
        Constructor requires the document ID (logid) for the log.
        This will usually be related to the VM (or other resource)
        being logged.

        The dbnode should be the host:port for contacting the
        database.  The bucket and password allow access to the
        appropriate part of the database.
        """
        super(CouchbaseHandler, self).__init__(level=log.INFO)

        couchbase = Couchbase(dbnode, bucket, password)
        self.bucket = couchbase[bucket]

        self.logid = logid
        try:
            bucket.add(self.logid, 0, 0, '')
        except:
            pass

    def emit(self, record):
        """
        Simply append the given record to the document within the
        database.
        """
        msg = self.format(record) + "\n"
        self.bucket.append(self.logid, msg)
