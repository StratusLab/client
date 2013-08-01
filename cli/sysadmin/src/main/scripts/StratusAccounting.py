import sys
sys.path.append('/var/lib/stratuslab/python')
import json
import requests
from couchbase.client import Couchbase

"""
view defined to get all documents by id
Querying views will be performed using REST API endpoint
Method	GET /bucket/_design/design-doc/_view/view-name
Method	PUT /bucket/_design/design-doc
Method	DELETE /bucket/_design/design-doc/_view/view-name
Below: bucket='default', design-doc='dev_byid', and view-name='by_id' 
"""
design_doc = {"views":
              {"by_id":
               {"map":
                '''function (doc, meta) {
                     emit(doc.id, null);
                   }'''
                },
               }
              }

view_tag='_design/dev_byid'


class StratusAccounting(object):
    """
    StratusAccount Class for retrieving StratusLab accounting records from Couchbase database
    """
    def __init__(self,
                 host='127.0.0.1:8091', bucket='default', password=''):
        self.host=host
        self.client = Couchbase(host, bucket, password)
        self.bucket = self.client[bucket]
   

    def get_usage_record(self,by_id):
        """
        Retrieve VM usage record from the Couchbase database.
        """
        record = self.bucket.get(by_id)
        return record

    def get_vm_usage(self, docid):
        """
        Get VM uuid, disk read and written, state, net_rx, net_tx, vcpu, cpu_time, name and memory.
        """

        vm_record=json.loads(self.get_usage_record(docid)[2]) 
        for k in vm_record.keys():
		print str(k).ljust(25), str(vm_record[k]).rjust(37)
   
    def get_vms_usage_byview(self,by_view):
        """
        Retrieve all VM usage records, in respect of by_view, from the Couchbase database.
        """

        records = self.bucket.view(by_view)
        for rec in records:
		self.get_vm_usage(rec['id'])
                print '---------------------------------------------------------------'
        


    def create_view(self, view_tag=view_tag, design_doc=design_doc):
        """
        Create view using REST API calls
        """
        view_url='http://%s:8092/default/%s' % (self.host, view_tag)
        data=json.dumps(design_doc)
        headers = {'content-type': 'application/json'}    
        r = requests.put(view_url, data=data, headers=headers)
        print r.text        



    def delete_view(self, view_tag=view_tag):
        """
        Delete view using REST API calls
        """
        view_url='http://%s:8092/default/%s' % (self.host, view_tag)
        headers = {'content-type': 'application/json'}
        r = requests.delete(view_url, headers=headers)
        print r.text



#myview="_design/dev_byid/_view/by_id"
#s_acc = StratusAccounting(host='onehost-5.lal.in2p3.fr')
#s_acc.create_view()
#sacc.get_vms_usage_byview(myview)
