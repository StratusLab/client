#!/usr/bin/python

import operator
import xml.etree.ElementTree as ET
from subprocess import check_output
import urllib2
import datetime

# Inputs

userId = 2
fromDate = [2013,05,04] # YYYY MM DD
toDate = [2013,05,30]


fromInSecs = (datetime.datetime(fromDate[0],fromDate[1],fromDate[2])-datetime.datetime(1970,1,1)).total_seconds()
toInSecs = (datetime.datetime(toDate[0],toDate[1],toDate[2])-datetime.datetime(1970,1,1)).total_seconds()

marketplaceSizeCache = {}

def get_all_vms_from_one():
    print 'Querying OpenNebula Accounting...'
    return check_output(["oneacct", "-u", str(userId), "-x"])

def get_vm_details_from_one(vmId):
    print 'Extracting OpenNebula VM details...'
    return check_output(["onevm", "show", str(vmId), "-x"])

def to_xml(xml_as_string):
    return ET.fromstring(xml_as_string)

def get_stime(vm):
    return vm.find('slice/stime').text

def get_id(vm):
    return vm.get('id')

def in_range(vm):
    stime = int(get_stime(vm))
    if fromInSecs and stime < fromInSecs:
        return False
    if toInSecs and stime > toInSecs:
        return False
    return True

def filter_vms(root):
    vms = []
    for vm in root.iter('vm'):
        if in_range(vm):
            slice = vm.find('slice')
            if slice is not None:
                stime = ET.Element('starttime')
                inSecs = int(slice.find('stime').text)
                stime.text = str(datetime.datetime.fromtimestamp(inSecs))
                vm.append(stime)
                vm.remove(slice)
            vms.append(vm)
    return vms
        
def bytes_to_giga_approximation(numberOfBytes):
    return (numberOfBytes / 1024**3) + 1

def get_sizes(vmDetail):
    disks = get_disks(vmDetail)
    sizes = [get_disk_size(disk) for disk in disks]
    return sizes

def insert_disks(vm, sizes):
    print 'Inserting disk info...'
    for size in sizes:
        diskElement = ET.Element('disk')
        sizeElement = ET.Element('size')
        sizeElement.text = str(size)
        diskElement.append(sizeElement)
        vm.append(diskElement)

def add_detail_info(vms):
    for vm in vms:
        vmDetail = to_xml(get_vm_details_from_one(get_id(vm)))
        sizes = get_sizes(vmDetail)
        insert_disks(vm, sizes)
        vm.find('name').text = vmDetail.find('NAME').text
    return vms

def get_disks(vm):
    return vm.findall('TEMPLATE/DISK')

def get_size_from_marketplace(disk):
    source = disk.find('SOURCE')
    url = source.text
    if url in marketplaceSizeCache:
        return marketplaceSizeCache[url]        
    print 'Retrieving marketplace info:', url, '...'
    marketplaceDefinition = urllib2.urlopen(url + '?status=all&location=all').read()
    root = ET.fromstring(marketplaceDefinition)
    bytes = root.find('rdf:RDF/rdf:Description/ns2:bytes', namespaces={"rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#","ns2":"http://mp.stratuslab.eu/slreq#"}).text
    bytes = int(bytes)
    marketplaceSizeCache[url] = bytes
    return bytes

def get_disk_size(disk):
    size = disk.find('SIZE')
    if size is not None:
        return float(size.text)/1024
    else:
        return bytes_to_giga_approximation(get_size_from_marketplace(disk))

def bytes_to_GB(bytes):
    return bytes / 1024 / 1024 / 1024

def compute_totals(root):
    totalTime = 0
    totalCpu = 0
    totalRam = 0
    totalDisk = 0
    totalNetRx = 0
    totalNetTx = 0

    for vm in root.findall('vm'):
        time = float(vm.find('time').text) / 60 / 60 # in hours
        totalTime += time
        totalCpu += float(vm.find('cpu').text) * time
        totalRam += float(vm.find('mem').text) * time / 1024
        totalNetRx += int(vm.find('net_rx').text)
        totalNetTx += int(vm.find('net_tx').text)
        disk = reduce(lambda a,b: a+b, [float(disk.find('size').text) for disk in vm.findall('disk')], 0)
        totalDisk += disk * time

    root.set('total_time', str("%.2f" % totalTime))
    root.set('total_cpu', str("%.2f" % totalCpu))
    root.set('total_ram', str("%.2f" % totalRam))
    root.set('total_disk', str("%.2f" % totalDisk))
    root.set('total_net_rx', str("%.2f" % (bytes_to_GB(totalNetRx))))
    root.set('total_net_tx', str("%.2f" % (bytes_to_GB(totalNetTx))))

vmsFromOne = get_all_vms_from_one()
allVms = to_xml(vmsFromOne)
filteredVms = filter_vms(allVms)
withDiskInfoVms = add_detail_info(filteredVms)

root = ET.Element('usagerecord')
root.set('userid', allVms.get('id'))
root.set('from', str(datetime.datetime.fromtimestamp(fromInSecs)))
if toInSecs:
    root.set('to', str(datetime.datetime.fromtimestamp(toInSecs)))

for vm in withDiskInfoVms:
    root.append(vm)

compute_totals(root)

print ET.dump(root)
