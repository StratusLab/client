#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2013, SixSq Sarl
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
import xml.etree.ElementTree as ET
import urllib2
import datetime
import time

from .one_query import get_all_users_from_one, get_all_vms_from_one, \
    get_vm_details_from_one


class Computer(object):

    # The queueing time of the VM instantiation request.
    VM_STARTTIME_ELEM = 'stime'
    VM_ENDTIME_ELEM = 'etime'
    VM_RUN_STARTTIME_ELEM = 'rstime'
    VM_RUN_ENDTIME_ELEM = 'retime'
    VM_EPILOG_ENDTIME_ELEM = 'eetime'

    USER_IGNORE_LIST = ['oneadmin']

    def __init__(self, fromInSecs, toInSecs, outputDir, daily,
                 stime_running=True, etime_done=True, user_names=[]):
        self.outputDir = outputDir
        self.daily = daily
        self.user_names = user_names
        self.marketplaceSizeCache = {}
        self.fromInSecs = int(fromInSecs)
        self.toInSecs = int(toInSecs)

        """Start time corresponds to the VM entering Running state. Alternative
        is to use get_stime() - time when the request for the VM instantiation
        was queued (Pending state)."""
        self.get_starttime = stime_running and self.get_rstime or self.get_stime

        """End time is when the VM stopped Running. Another option is to use
        get_donetime() which takes into account Epilog."""
        self.get_endtime = etime_done and self.get_donetime or self.get_retime

    def get_stime(self, vm):
        return int(vm.find('slice/' + self.VM_STARTTIME_ELEM).text)

    def get_rstime(self, vm):
        return int(vm.find('slice/' + self.VM_RUN_STARTTIME_ELEM).text)

    def get_retime(self, vm):
        return int(vm.find('slice/' + self.VM_RUN_ENDTIME_ELEM).text)

    def get_eetime(self, vm):
        return int(vm.find('slice/' + self.VM_EPILOG_ENDTIME_ELEM).text)

    def get_etime(self, vm):
        return int(vm.find('slice/' + self.VM_ENDTIME_ELEM).text)

    def get_etime_vm_details(self, vm):
        return int(vm.find('ETIME').text)

    def get_donetime(self, vm):
        retime = self.get_retime(vm)
        eetime = self.get_eetime(vm)
        etime = (eetime > retime) and eetime or retime
        if etime == 0:
            etime = self.get_etime(vm)
            # The VM might have failed to start. In this case 'ETIME' is set
            # on the VM details only taken from ONE DB by 'onevm'. This looks
            # like a bug in 'oneacctd' or 'oneacct'.
            if etime == 0:
                etime = self._query_etime_from_vm_details(vm)
        return etime

    def _query_etime_from_vm_details(self, vm):
        vm_details = get_vm_details_from_one(self.get_id(vm))
        return self.get_etime_vm_details(vm_details)

    def get_id(self, vm):
        return vm.get('id')

    def vm_in_range(self, vm):
        """Filter out VMs that were stopped before or started after the time
        slice we are concerned with."""
        endtime = int(self.get_endtime(vm))
        # endtime == 0 assumes that the VM is still running or didn't run
        if endtime > 0 and endtime < self.fromInSecs:  # ended before metering window
            return False
        starttime = int(self.get_starttime(vm))
        if starttime > self.toInSecs:  # started after metering window
            return False
        if starttime == 0:  # VM didn't run
            stime = self.get_stime(vm)
            if stime > self.fromInSecs and stime < self.toInSecs:
                return True
            else:
                return False
        return True

    def user_in_range(self, user):
        username = user.findtext('NAME')
        return self.username_in_range(username)

    def username_in_range(self, username):
        if username in self.USER_IGNORE_LIST:
            print 'skipping', username
            return False
        return True

    def filter_users(self, root):
        def _append_user(_users, u):
            user = {}
            user['id'] = u.findtext('ID')
            user['name'] = u.findtext('NAME')
            _users.append(user)
        users = []
        if root is not None:
            if self.user_names:
                cloud_users = dict((u.findtext('NAME'), u) for u in root.findall('USER'))
                for name in self.user_names:
                    if self.username_in_range(name):
                        try:
                            u = cloud_users[name]
                        except KeyError:
                            print 'WARNING: user %s not found.' % name
                        else:
                            _append_user(users, cloud_users[name])
            else:
                for u in root.getiterator('USER'):
                    if self.user_in_range(u):
                        _append_user(users, u)
        return users

    def filter_and_update_vms(self, root):
        vms = []
        if root is not None:
            for vm in root.getiterator('vm'):
                if self.vm_in_range(vm):
                    self._update_time_on_vm(vm)
                    vms.append(vm)
        return vms

    def _update_time_on_vm(self, vm):
        _slice = vm.find('slice')
        if _slice is None:
            print 'time for missing slice:', vm.findtext('time')
            timeElem = vm.find('time')
            timeElem.text = "XX"
        else:
            meter_stime, meter_etime = self.get_meter_start_end_times(vm)

            self.set_starttime(vm, meter_stime)
            self.set_endtime(vm, meter_etime)
            # Total time should be in hours
            delta = int((meter_etime - meter_stime) / 60 / 60)
            self.set_totaltime(vm, (delta > 0) and delta or 0)

            vm.remove(_slice)

    def get_meter_start_end_times(self, vm):
        stime = self.get_starttime(vm)
        etime = self.get_endtime(vm)
        if stime == etime:  # VM didn't run
            meter_stime = self.get_stime(vm)
            meter_etime = self.get_etime(vm)
        else:
            meter_stime = self.get_meter_stime(vm)
            meter_etime = self.get_meter_etime(vm)
        return meter_stime, meter_etime

    def get_meter_stime(self, vm):
        stime = self.get_starttime(vm)
        if stime == 0:  # VM didn't run
            stime = self.get_stime(vm)
        if self.fromInSecs > stime:
            return self.fromInSecs
        else:
            return stime

    def get_meter_etime(self, vm):
        etime = self.get_endtime(vm)
        if etime == 0:  # Machine is still running or didn't run
            return self.toInSecs
        if etime < self.toInSecs:
            return etime
        else:
            return self.toInSecs

    def set_totaltime(self, vm, _time):
        time_elem = vm.find('time')
        time_elem.text = str(_time)

    def set_starttime(self, vm, starttime):
        self._vm_set_time_in_sec(vm, starttime, 'starttime')

    def set_endtime(self, vm, endtime):
        self._vm_set_time_in_sec(vm, endtime, 'endtime')

    def _vm_set_time_in_sec(self, vm, _time, time_elem_name):
        time_elem = ET.Element(time_elem_name)
        time_elem.text = str(datetime.datetime.utcfromtimestamp(float(_time)))
        vm.append(time_elem)

    def bytes_to_giga_approximation(self, numberOfBytes):
        return (numberOfBytes / 1024 ** 3) + 1

    def get_sizes(self, vmDetail):
        disks = self.get_disks(vmDetail)
        sizes = [self.get_disk_size(disk) for disk in disks]
        return sizes

    def insert_disks(self, vm, sizes):
        for size in sizes:
            diskElement = ET.Element('disk')
            sizeElement = ET.Element('size')
            sizeElement.text = str(size)
            diskElement.append(sizeElement)
            vm.append(diskElement)

    def add_detail_info(self, vms):
        for vm in vms:
            vmDetail = get_vm_details_from_one(self.get_id(vm))
            if vmDetail is not None:
                sizes = self.get_sizes(vmDetail)
                self.insert_disks(vm, sizes)
                vm.find('name').text = vmDetail.find('NAME').text
        return vms

    def get_disks(self, vm):
        return vm.findall('TEMPLATE/DISK')

    def get_size_from_marketplace(self, url):
        if url in self.marketplaceSizeCache:
            return self.marketplaceSizeCache[url]
        try:
            marketplaceDefinition = self._get_url(url + '?status=all&location=all')
        except urllib2.URLError as ex:
            _bytes = 0
            print "Error retrieving marketplace url:", url, ex
        else:
            root = ET.fromstring(marketplaceDefinition)
            _bytes = root.find('{0}RDF/{0}Description/{1}bytes'.\
                               format("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}",
                                      "{http://mp.stratuslab.eu/slreq#}")).text
            _bytes = int(_bytes)
        self.marketplaceSizeCache[url] = _bytes
        return _bytes

    def _get_url(self, url):
        """Raises urllib2.URLError"""
        return urllib2.urlopen(url).read()

    def get_disk_size(self, disk):
        size = disk.find('SIZE')
        if size is not None:
            return float(size.text) / 1024
        else:
            return self.bytes_to_giga_approximation(
                self.get_size_from_marketplace(self.get_disk_source(disk)))

    def get_disk_source(self, disk):
        return disk.find('SOURCE').text.strip()

    def bytes_to_GB(self, _bytes):
        return _bytes / 1024 / 1024 / 1024

    def compute_totals(self, root):
        totalTime = 0
        totalCpu = 0
        totalRam = 0
        totalDisk = 0
        totalNetRx = 0
        totalNetTx = 0

        for vm in root.findall('vm'):
            time = float(vm.find('time').text)  # in hours
            totalTime += time
            totalCpu += float(vm.find('cpu').text) * time
            totalRam += float(vm.find('mem').text) * time / 1024
            totalNetRx += int(vm.find('net_rx').text)
            totalNetTx += int(vm.find('net_tx').text)
            disk = reduce(lambda a, b: a + b, [float(disk.find('size').text) for disk in vm.findall('disk')], 0)
            totalDisk += disk * time

        root.set('total_time', str("%.0f" % totalTime))
        root.set('total_cpu', str("%.0f" % totalCpu))
        root.set('total_ram', str("%.0f" % totalRam))
        root.set('total_disk', str("%.0f" % totalDisk))
        root.set('total_net_rx', str("%.0f" % (self.bytes_to_GB(totalNetRx))))
        root.set('total_net_tx', str("%.0f" % (self.bytes_to_GB(totalNetTx))))

    def get_users(self):
        return self.filter_users(get_all_users_from_one())

    def _append_vms(self, root, allVms):
        if allVms is not None:
            filteredVms = self.filter_and_update_vms(allVms)
            withDiskInfoVms = self.add_detail_info(filteredVms)

            for vm in withDiskInfoVms:
                root.append(vm)

    def compute_user(self, user):
        _id = user['id']
        username = user['name']
        print 'processing', username, '...'
        allVms = get_all_vms_from_one(_id)
        root = ET.Element('usagerecord')

        self._append_vms(root, allVms)

        root.set('userid', _id)
        root.set('username', username)
        _from = datetime.datetime.utcfromtimestamp(self.fromInSecs)
        root.set('from', str(_from))
        to = datetime.datetime.utcfromtimestamp(self.toInSecs)
        root.set('to', str(to))

        self.compute_totals(root)
        dateFormat = '%d%m%Y'
        hourFormat = '%H%M%S'
        filenameTemplate = "acctpy_User-Id%(id)s_%(date)s.xml"
        if(self.daily):
            formattedDate = to.strftime(dateFormat)
            filename = os.path.join(self.outputDir, filenameTemplate % \
                                    {'id': _id, 'date': formattedDate})
        else:
            formattedDate = _from.strftime(dateFormat) + '_' + \
                _from.strftime(hourFormat) + '-' + to.strftime(hourFormat)
            filename = os.path.join(self.outputDir, filenameTemplate % \
                                    {'id': _id, 'date': formattedDate})
        open(filename, 'w').write(ET.tostring(root))

    def compute(self):
        for user in self.get_users():
            try:
                self.compute_user(user)
            except Exception as ex:
                _time = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime(time.time()))
                print _time, "Error processing user", user['name']
                print ex
        return
