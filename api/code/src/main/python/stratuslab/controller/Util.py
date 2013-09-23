#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
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

import os
import time

from ConfigParser import SafeConfigParser

from couchbase import Couchbase

from stratuslab import Defaults

CB_CFG_PATH = os.path.join(Defaults.ETC_DIR, 'couchbase.cfg')

HEARTBEAT_TTL = 2 * 60 * 60  # two hours in seconds


def read_cb_cfg(service_name, cfg_path=CB_CFG_PATH, default_docid=None):
    """
    Returns a ConfigParser containing the Couchbase connection
    parameters for a service.
    """
    cfg = SafeConfigParser({'host': 'localhost:8091',
                            'bucket': 'default',
                            'password': '',
                            'docid': default_docid})

    cfg.read(cfg_path)

    if not cfg.has_section(service_name):
        service_name = 'DEFAULT'

    params = {'host': cfg.get(service_name, 'host'),
              'bucket': cfg.get(service_name, 'bucket'),
              'password': cfg.get(service_name, 'password'),
              'docid': cfg.get(service_name, 'docid')
    }

    return params


def get_cb_client(**kwargs):
    return Couchbase.connect(host=kwargs['host'], bucket=kwargs['bucket'], password=kwargs['password'])


def heartbeat(cb_client, docid, status='OK', message='OK', ttl=HEARTBEAT_TTL):
    """
    Emits a heartbeat message for a service with the current
    UTC time as the timestamp.
    """
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    data = {'status': status,
            'timestamp': timestamp,
            'message': message}
    cb_client.set(docid, data, ttl)


def claim_job(cb_client, docid, executor):
    """
    Will change the given job (identified by the docid) from the
    QUEUED to the RUNNING state.  It will also add a property
    ('sl_executor') identifying the daemon claiming the job.

    Returns True if the job was successfully claimed; False otherwise.
    """
    try:
        retry_update_job(cb_client, docid, state='RUNNING', executor=executor)
        return True
    except Exception:
        return False


def retry_update_job(cb_client, docid, state,
                     previous_state='QUEUED', progress=0, msg=None, executor=None, retries=3):
    for i in range(0, retries):
        try:
            update_job(cb_client, docid, state,
                       previous_state=previous_state, progress=progress, msg=msg,
                       executor=executor)
        except ConcurrentModificationException:
            time.sleep(2)


def update_job(cb_client, docid, state,
               previous_state='QUEUED', progress=0, msg=None, executor=None):
    """
    Updates the given job by updating the state, progress, and
    message.
    """
    rv = cb_client.get(docid)

    if not rv.success:
        raise Exception('cannot retrieve job %s' % docid)

    job = rv.value

    try:
        current_state = job['state']
        if current_state != previous_state:
            msg = 'job is not in the expected state (%s); ' \
                  'current state is %s' \
                  % (previous_state, current_state)
            raise Exception(msg % (previous_state, current_state))
    except Exception:
        raise Exception('malformed job without a state value')

    # update the job record
    job['state'] = state
    job['progress'] = progress
    if msg is not None:
        job['statusMessage'] = msg

    if executor is not None:
        properties = job.get('properties', {})
        properties['sl_executor'] = executor
        job['properties'] = properties

    try:
        # write updates back to database
        cb_client.replace(docid, job, cas=rv.cas)
    except couchbase.exceptions.KeyExistsError:
        raise ConcurrentModificationException()
    except couchbase.exceptions.NotFoundError:
        raise Exception('job deleted during update')


class ConcurrentModificationException(Exception):
    pass
