from mock.mock import Mock
import unittest
import json
import xml.etree.ElementTree as ET
import os

from stratuslab.accounting import one_query

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

USER_VM_FILE = os.path.join(SCRIPT_DIR, 'user_vm.json')
USER_VMS_FILE = os.path.join(SCRIPT_DIR, 'user_vms.json')


class TestOneQuery(unittest.TestCase):

    def test_user_vms_dict2et_none(self):
        assert None == one_query._user_vms_dict2et({})

    def test_user_vms_dict2et(self):
        user_vm_dict = json.loads(self._get_single_vm_as_json())
        user_vm_etree = one_query._user_vms_dict2et(user_vm_dict)
        assert isinstance(user_vm_etree, ET.Element)
        assert 'user' == user_vm_etree.tag
        assert 1 == len(user_vm_etree.getiterator('vm'))

        user_vms_dict = json.loads(self._get_multiple_vms_as_json())
        user_vms_etree = one_query._user_vms_dict2et(user_vms_dict)
        assert isinstance(user_vm_etree, ET.Element)
        assert 'user' == user_vms_etree.tag
        assert 2 == len(user_vms_etree.getiterator('vm'))

    def test_get_all_vms_from_one(self):
        one_query._get_all_vms_from_one_json = \
            Mock(return_value='')
        assert None == one_query.get_all_vms_from_one('007')

        one_query._get_all_vms_from_one_json = \
            Mock(return_value=self._get_single_vm_as_json())
        user_vm_etree = one_query.get_all_vms_from_one('007')
        assert isinstance(user_vm_etree, ET.Element)
        assert 'user' == user_vm_etree.tag
        assert 1 == len(user_vm_etree.getiterator('vm'))

    def _get_multiple_vms_as_json(self):
        return open(USER_VMS_FILE).read()

    def _get_single_vm_as_json(self):
        return open(USER_VM_FILE).read()

if __name__ == "__main__":
    unittest.main()
