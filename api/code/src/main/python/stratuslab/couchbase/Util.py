import json
import requests




def create_views(host,bucket,design_doc,map_view):
    """
    Create views within a design document using REST API calls
    """
    view_url='http://%s:8092/%s/_design/%s' % (host,bucket,design_doc)
    data=json.dumps(map_view)
    headers = {'content-type': 'application/json'}
    r = requests.put(view_url, data=data, headers=headers)
    print r.text



def delete_designdoc(host,bucket,design_doc):
    """
    Delete design doc using REST API calls
    """
    view_url='http://%s:8092/%s/_design/%s' % (host,bucket,design_doc)
    headers = {'content-type': 'application/json'}
    r = requests.delete(view_url, headers=headers)
    print r.text

