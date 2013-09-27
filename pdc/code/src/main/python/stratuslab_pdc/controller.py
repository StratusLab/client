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

import time

import couchbase
from couchbase.views.iterator import View
from couchbase.views.params import Query

import stratuslab.controller.util as Util
from stratuslab.controller.base_controller import BaseController

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.volume_manager_factory import VolumeManagerFactory


class Controller(BaseController):
    def __init__(self):
        BaseController.__init__(self, 'sl-pdc', 'Configuration/sl-pdc')

    def _validate_service_cfg(self, cfg):
        required_keys = ['pdisk_username', 'pdisk_password', 'pdisk_endpoint']
        for k in required_keys:
            if not k in cfg or not cfg[k]:
                raise Exception('%s missing or empty in configuration' % k)

    def _jobs(self):

        # get queued jobs from the database
        q = Query(mapkey_range=['Job/', 'Job/' + Query.STRING_RANGE_END])
        results = View(self.cb, 'cimi.0', 'doc-id', include_docs=True, query=q)

        relevant_jobs = []
        for result in results:
            job = result.doc.value
            if job is not None:
                try:
                    if job['state'] == 'QUEUED':
                        if job['targetResource'].startswith('Volume/'):
                            action = job['action']
                            if action == 'create' or action == 'delete':
                                relevant_jobs.append(job)
                except KeyError:
                    pass

        return relevant_jobs

    def _claim(self, job):
        job_id = self._job_id(job)
        rv = Util.claim_job(self.cb, job_id, self.executor)
        self.logger.debug('claim result for %s is %s' % (job_id, str(rv)))
        return rv

    def _execute(self, job):
        job_id = self._job_id(job)
        action = str(job['action'])
        if action == 'create':
            self._create_volume(job)
        elif action == 'delete':
            self._delete_volume(job)
        else:
            self.logger.error('attempt to execute job (%s) with unknown action (%s)' % (job_id, action))

    def _set_job_error(self, job_id, msg):
        self.logger.error(msg)
        try:
            Util.retry_update_job(self.cb, job_id, state='FAILED',
                                  previous_state='RUNNING', progress=100,
                                  msg=msg, executor=self.executor)
        except Exception as e:
            self.logger.error('cannot update %s: %s' % (job_id, str(e)))

    @staticmethod
    def kb_to_gb(kbytes):
        nbytes = 1000 * kbytes
        if nbytes < 0:
            nbytes = 0
        bytes_in_gbyte = pow(10, 9)
        gbytes = int(nbytes / bytes_in_gbyte)
        if gbytes == 0 or (nbytes % bytes_in_gbyte) > 0:
            gbytes += 1

        return gbytes

    def update_volume_state(self, vol_docid, volume, cas, state, sl_uuid=None, msg=None):

        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        volume['state'] = state
        volume['updated'] = timestamp

        if sl_uuid:
            properties = volume.get('properties', {})
            properties['sl_uuid'] = sl_uuid
            volume['properties'] = properties

        if msg:
            properties = volume.get('properties', {})
            properties['sl_msg'] = msg
            volume['properties'] = properties

        try:
            self.cb.set(vol_docid, volume, cas=cas)
        except couchbase.exceptions.KeyExistsError:
            self.logger.error('attempt at concurrent modification of %s' % vol_docid)

    def _create_volume(self, job):
        job_id = self._job_id(job)
        vol_docid = str(job['targetResource'])
        self.logger.info('creating %s' % vol_docid)

        try:
            rv = self.cb.get(vol_docid)
            cas = rv.cas
            volume = rv.value
        except couchbase.exceptions.NotFoundError:
            msg = 'cannot retrieve %s' % vol_docid
            self._set_job_error(job_id, msg)
            return

        try:
            kbytes = volume['capacity']
        except KeyError:
            msg = 'volume is missing capacity value'
            self._set_job_error(job_id, msg)
            self.update_volume_state(vol_docid, volume, cas, 'ERROR', msg=msg)
            return

        size = Controller.kb_to_gb(kbytes)

        try:
            tag = str(volume['name'])
        except KeyError:
            tag = None

        config_holder = ConfigHolder(config=self.cfg)

        try:
            pdisk = VolumeManagerFactory.create(config_holder)

            sl_uuid = pdisk.createVolume(size, tag, 'private')
        except Exception as e:
            msg = 'error creating volume: %s' % str(e)
            self._set_job_error(job_id, msg)
            self.update_volume_state(vol_docid, volume, cas, 'ERROR', msg=str(e))
            return

        self.logger.info('created pdisk uuid %s' % str(sl_uuid))

        self.update_volume_state(vol_docid, volume, cas, 'AVAILABLE', sl_uuid=sl_uuid)

        try:
            Util.retry_update_job(self.cb, job_id, state='SUCCESS',
                                  previous_state='RUNNING', progress=100,
                                  msg='OK', executor=self.executor)
        except Exception as e:
            self.logger.error('cannot update %s: %s' % (job_id, str(e)))

    def _delete_volume(self, job):
        job_id = self._job_id(job)
        vol_docid = str(job['targetResource'])
        self.logger.info('deleting %s' % vol_docid)

        try:
            rv = self.cb.get(vol_docid)
            cas = rv.cas
            volume = rv.value
        except couchbase.exceptions.NotFoundError:
            msg = 'cannot retrieve %s' % vol_docid
            self._set_job_error(job_id, msg)
            return

        try:
            sl_uuid = str(volume['properties']['sl_uuid'])
        except Exception:
            msg = 'volume is missing sl_uuid property'
            self._set_job_error(job_id, msg)
            return

        config_holder = ConfigHolder(config=self.cfg)

        try:
            pdisk = VolumeManagerFactory.create(config_holder)
            pdisk.deleteVolume(sl_uuid)
        except Exception as e:
            msg = 'error deleting sl_uuid %s: %s' % (sl_uuid, str(e))
            self._set_job_error(job_id, msg)
            return

        try:
            self.cb.delete(vol_docid, cas=cas)
        except couchbase.exceptions.KeyExistsError:
            msg = 'cannot delete %s' % vol_docid
            self._set_job_error(job_id, msg)
            return

        try:
            Util.retry_update_job(self.cb, job_id, state='SUCCESS',
                                  previous_state='RUNNING', progress=100,
                                  msg='OK', executor=self.executor)
        except Exception as e:
            self.logger.error('cannot update %s: %s' % (job_id, str(e)))
