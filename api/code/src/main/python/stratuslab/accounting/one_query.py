import json
import commands
import xml.etree.ElementTree as ET


def get_all_users_from_one():
    '''Return ElementTree representation of all users.
    '''
    xml = _run_command("oneuser list -x")
    return _xml_to_etree(xml)


def get_vm_details_from_one(vm_id):
    '''Return ElementTree representation of VM.
    '''
    xml = _run_command("onevm show %s -x" % str(vm_id))
    return _xml_to_etree(xml)


def get_all_vms_from_one(user_id):
    '''Return ElementTree representation of all VMs of the user.
    '''
    user_vms_json = _get_all_vms_from_one_json(user_id)
    if user_vms_json:
        return _user_vms_dict2et(json.loads(user_vms_json))
    return None


def _get_all_vms_from_one_json(user_id):
    return _run_command("oneacct -u %s -j" % str(user_id))


def _run_command(cmd):
    rc, output = commands.getstatusoutput(cmd)
    if rc != 0:
        raise Exception('Failed: %s' % output)
    return output


def _xml_to_etree(xml_as_string):
    '''Return ElementTree representation of the XML provided as string.
    '''
    etree = None
    if xml_as_string.strip():
        etree = ET.fromstring(xml_as_string)
    return etree


def _user_vms_dict2et(user_vms):
    if not user_vms:
        return
    user = ET.Element('user')
    uid = user_vms.keys()[0]
    user.set('id', uid)
    for vmid, data in user_vms[uid]['vms'].items():
        vm = ET.SubElement(user, 'vm')
        vm.set('id', str(vmid))
        ET.SubElement(vm, 'name')
        _time = ET.SubElement(vm, 'time')
        _time.text = unicode(data['time'])
        cpu = ET.SubElement(vm, 'cpu')
        mem = ET.SubElement(vm, 'mem')
        net_rx = ET.SubElement(vm, 'net_rx')
        net_rx.text = unicode(data['network']['net_rx'])
        net_tx = ET.SubElement(vm, 'net_tx')
        net_tx.text = unicode(data['network']['net_tx'])
        # Only one slice is used
        _slice = ET.SubElement(vm, 'slice')
        _slice.set('seq', '0')
        for k, v in data['slices'][0].items():
            elem = ET.SubElement(_slice, k)
            elem.text = unicode(v)
            if k == 'cpu':
                cpu.text = elem.text
            if k == 'mem':
                mem.text = elem.text
    return user

'''
For the reference: the XML representation of the user VMs.
<?xml version="1.0"?>
<user id="6">
  <vm id="417">
    <name/>
    <time>148</time> <!-- What is this? -->
    <cpu>1.0</cpu>
    <mem>1536</mem>
    <net_rx>2363337</net_rx>
    <net_tx>147185</net_tx>
    <slice seq="0">
      <retime>1390935613</retime>
      <petime>1390935465</petime>
      <uid>6</uid>
      <estime>0</estime>
      <rstime>1390935465</rstime>
      <vcpu>1</vcpu>
      <mem>1536</mem>
      <gid>1</gid>
      <eetime>0</eetime>
      <hid>26</hid>
      <etime>0</etime>
      <hostname>192.168.112.28</hostname>
      <cpu>1.0</cpu>
      <name>orchestrator-atos-es1:d9d36bb6-5046-461c-bfec-b68a6d86c2c0</name>
      <reason>3</reason>
      <seq>0</seq>
      <id>417</id>
      <pstime>1390935445</pstime>
      <stime>1390935422</stime>
      <vm_id>417</vm_id>
    </slice>
  </vm>
  <vm id="418">
    <name/>
    <time>1390936218</time>
    <cpu>1.0</cpu>
    <mem>1024</mem>
    <net_rx>7705131</net_rx>
    <net_tx>91795</net_tx>
    <slice seq="0">
      <retime>1390936218</retime>
      <petime>0</petime>
      <uid>6</uid>
      <estime>0</estime>
      <rstime>0</rstime>
      <vcpu>1</vcpu>
      <mem>1024</mem>
      <gid>1</gid>
      <eetime>0</eetime>
      <hid>19</hid>
      <etime>0</etime>
      <hostname>192.168.112.21</hostname>
      <cpu>1.0</cpu>
      <name>apache.1:d9d36bb6-5046-461c-bfec-b68a6d86c2c0</name>
      <reason>3</reason>
      <seq>0</seq>
      <id>418</id>
      <pstime>0</pstime>
      <stime>1390935513</stime>
      <vm_id>418</vm_id>
    </slice>
  </vm>
</user>
'''
