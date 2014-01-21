#!/usr/bin/python

import sys
import os
import operator
import xml.etree.ElementTree as ET
import commands
import urllib2
import datetime

from optparse import OptionParser

class Computer(object):

    def __init__(self, fromInSecs, toInSecs, outputDir, daily):
        self.outputDir = outputDir
	self.daily = daily
        self.marketplaceSizeCache = {}
        self.fromInSecs = fromInSecs
        self.toInSecs = toInSecs

    def run_command(self, cmd):
        rc, output = commands.getstatusoutput(cmd)
        if rc != 0:
           raise Exception('Failed: %s' % output)
        return output

    def get_all_users_from_one(self):
        return self.run_command("oneuser list -x")

    def get_all_vms_from_one(self, userId):
        return self.run_command("oneacct -u %s -x" % str(userId))

    def get_vm_details_from_one(self, vmId):
        return self.run_command("onevm show %s -x" % str(vmId))

    def to_xml(self, xmlAsString):
        xml = None
        if xmlAsString.strip():
            xml = ET.fromstring(xmlAsString)
        return xml

    def get_stime(self, vm):
        return vm.find('slice/stime').text

    def get_id(vm):
        return vm.get('id')

    def vm_in_range(self, vm):
        stime = int(self.get_stime(vm))
        if self.fromInSecs and stime < self.fromInSecs:
            return False
        if self.toInSecs and stime > self.toInSecs:
            return False
        return True

    def user_in_range(self, user):
        ignore = ['oneadmin']
        username = user.findtext('NAME')
        if username in ignore:
            print 'skipping', username
            return False
        return True

    def filter_users(self, root):
        users = []
        if root is not None:
            for u in root.getiterator('USER'):
                if self.user_in_range(u):
                    user = {}
                    user['id'] = u.findtext('ID')
                    user['name'] = u.findtext('NAME')
                    users.append(user)
        return users

    def filter_vms(self, root):
        vms = []
        if root is not None:
            for vm in root.getiterator('vm'):
                if self.vm_in_range(vm):
                    timeElem = vm.find('time')
                    timeElem.text = str(float(timeElem.text) / 60 / 60) # in hours
                    slice = vm.find('slice')
                    if slice is None:
                        print 'time for missing slice:', vm.findtext('time')
                        timeElem.text = "XX"
                    else:
                        stime = ET.Element('starttime')
                        stimeInSecs = int(slice.findtext('stime'))
                        stime.text = str(datetime.datetime.fromtimestamp(stimeInSecs))
                        vm.append(stime)
                        etime = ET.Element('endtime')
                        etimeInSecs = int(slice.findtext('etime'))
                        etime.text = str(datetime.datetime.fromtimestamp(etimeInSecs))
                        vm.append(etime)
                        delta = (etimeInSecs - stimeInSecs) / 60 / 60 # in hours
                        if delta < 0:
                            delta = 0
                        timeElem.text = str(delta) # add one to round up
                        vm.remove(slice)
                    vms.append(vm)
        return vms

    def bytes_to_giga_approximation(self, numberOfBytes):
        return (numberOfBytes / 1024**3) + 1

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
            vmDetail = self.to_xml(get_vm_details_from_one(get_id(vm)))
            if vmDetail is not None:
                sizes = self.get_sizes(vmDetail)
                self.insert_disks(vm, sizes)
                vm.find('name').text = vmDetail.find('NAME').text
        return vms

    def get_disks(self, vm):
        return vm.findall('TEMPLATE/DISK')

    def get_size_from_marketplace(self, disk):
        source = disk.find('SOURCE')
        url = source.text
        if url in marketplaceSizeCache:
            return marketplaceSizeCache[url]
        try:
            marketplaceDefinition = urllib2.urlopen(url + '?status=all&location=all').read()
            root = ET.fromstring(marketplaceDefinition)
            bytes = root.find('rdf:RDF/rdf:Description/ns2:bytes', namespaces={"rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#","ns2":"http://mp.stratuslab.eu/slreq#"}).text
            bytes = int(bytes)
        except (urllib2.URLError, ValueError):
            bytes = 0
            print "Error retrieving marketplace url:", url
        marketplaceSizeCache[url] = bytes
        return bytes

    def get_disk_size(self, disk):
        size = disk.find('SIZE')
        if size is not None:
            return float(size.text)/1024
        else:
            return bytes_to_giga_approximation(get_size_from_marketplace(disk))

    def bytes_to_GB(self, bytes):
        return bytes / 1024 / 1024 / 1024

    def compute_totals(self, root):
        totalTime = 0
        totalCpu = 0
        totalRam = 0
        totalDisk = 0
        totalNetRx = 0
        totalNetTx = 0

        for vm in root.findall('vm'):
            time = float(vm.find('time').text) # in hours
            totalTime += time
            totalCpu += float(vm.find('cpu').text) * time
            totalRam += float(vm.find('mem').text) * time / 1024
            totalNetRx += int(vm.find('net_rx').text)
            totalNetTx += int(vm.find('net_tx').text)
            disk = reduce(lambda a,b: a+b, [float(disk.find('size').text) for disk in vm.findall('disk')], 0)
            totalDisk += disk * time

        root.set('total_time', str("%.0f" % totalTime))
        root.set('total_cpu', str("%.0f" % totalCpu))
        root.set('total_ram', str("%.0f" % totalRam))
        root.set('total_disk', str("%.0f" % totalDisk))
        root.set('total_net_rx', str("%.0f" % (self.bytes_to_GB(totalNetRx))))
        root.set('total_net_tx', str("%.0f" % (self.bytes_to_GB(totalNetTx))))

    def get_users(self):
        return self.filter_users(self.to_xml(self.get_all_users_from_one()))

    def compute_user(self, user):
        id = user['id']
        username = user['name']
        print 'processing', username, '...'
        vmsFromOne = self.get_all_vms_from_one(id)
        allVms = self.to_xml(vmsFromOne)
        root = ET.Element('usagerecord')
        if allVms is not None:
            filteredVms = self.filter_vms(allVms)
            withDiskInfoVms = self.add_detail_info(filteredVms)

            for vm in withDiskInfoVms:
                root.append(vm)

        root.set('userid', id)
        root.set('username', username)
        _from = datetime.datetime.fromtimestamp(self.fromInSecs)
        root.set('from', str(_from))
        to = datetime.datetime.fromtimestamp(self.toInSecs)
        root.set('to', str(to))

        self.compute_totals(root)
	dateFormat = '%d%m%Y'
	hourFormat = '%H%M%S'
	filenameTemplate = "acctpy_User-Id%(id)s_%(date)s.xml"
        if(self.daily):
	    formattedDate = to.strftime(dateFormat)
            filename = os.path.join(self.outputDir, filenameTemplate % {'id': id, 'date': formattedDate})
        else:
	    formattedDate = _from.strftime(dateFormat) + '_' + _from.strftime(hourFormat) + '-' + to.strftime(hourFormat)
	    filename = os.path.join(self.outputDir, filenameTemplate % {'id': id, 'date': formattedDate})
        open(filename,'w').write(ET.tostring(root))

    def compute(self):
        for user in self.get_users():
            try:
                self.compute_user(user)
            except Exception as ex:
                print "Error processing user", user['name']
                print ex
        return

class MainProgram():
    '''A command-line program to extract accounting data from StratusLab.'''

    def __init__(self, argv=None):
        self.lastNoOfHours = None
        self.outputDir = None
        self.parser = OptionParser()
        self.parse()
        self.do_work()

    def parse(self):
        usage = '''usage: %prog <last-no-of-hours>

<last-no-of-hours>  Number of hours from when to calculate accounting data for each user.'''

        self.parser.add_option('-d', '--output-dir', dest='outputDir',
                               help='Directory in which to generate the accounting files. Default to local directory.',
                               default='.')

        self.parser.usage = usage
        self.options, self.args = self.parser.parse_args()
        self._check_args()

    def _check_args(self):
        if len(self.args) > 1:
            self.usage_exit_too_many_arguments()
        if len(self.args) < 1:
            self.usage_exit_too_few_arguments()
        try:
            self.lastNoOfHours = int(self.args[0])
        except:
            print "invalid <last-no-of-hours> format"
            self._exit(2)
	if self.lastNoOfHours > 24:
	    print "Invalid <last-no-of-hours>, cannot be more than 24"
        if self.lastNoOfHours < 1:
            print "Invalid <last-no-of-hours>, cannot be less than 1"
        self.outputDir = self.options.outputDir

    def usage_exit_too_many_arguments(self):
        self.usage_exit("Too many arguments")

    def usage_exit_too_few_arguments(self):
        self.usage_exit("Too few arguments")

    def usage_exit(self, msg=None):
        if msg:
            print msg, '\n'
        self.parser.print_help()

        self._exit(1)

    def _exit(self, code):
        sys.exit(code)

    def do_work(self):
        refDate = datetime.datetime(1970,1,1)
        now = datetime.datetime.now()
        delta = datetime.timedelta(hours=self.lastNoOfHours)

        fromInSecs = self.total_seconds(now - delta - refDate)
        toInSecs = self.total_seconds(now - refDate)

	if self.lastNoOfHours == 24:
	    daily = True
	else:
	    daily = False
        Computer(fromInSecs, toInSecs, self.outputDir, daily).compute()

    def total_seconds(self, td):
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

main = MainProgram

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
