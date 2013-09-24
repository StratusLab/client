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

from couchbase.views.iterator import View
from couchbase.views.params import Query

from stratuslab.controller.base_controller import BaseController


class Controller(BaseController):
    def __init__(self):
        BaseController.__init__(self, 'sl-pdc', 'Configuration/sl-pdc')

    def _validate_service_cfg(self):
        pass

    def _jobs(self):

        # get queued jobs from the database
        q = Query(mapkey_range=['Job/', 'Job/' + Query.STRING_RANGE_END])
        results = View(self.cb, 'cimi.0', 'doc-id', include_docs=True, query=q)

        relevant_jobs = []
        for result in results:
            job = result.doc.value
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
        return True

    def _execute(self, job):
        self.logger.info('executing job: %s' % self._job_id(job))
