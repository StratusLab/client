'''
Created on Jul 5, 2011

@author: vagos
'''
import urllib2 
try:
    from hashlib import sha1 as _sha, md5 as _md5
except ImportError:
    import sha
    import md5
    _sha = sha.new
    _md5 = md5.new
import argparse

class NFSClient():
    def __init__(self):
        pass
#        proxy_handler = urllib2.ProxyDigestAuthHandler()
#        proxy_auth_handler = urllib2.HTTPDigestAuthHandler()
#        proxy_auth_handler.add_password('StratusLab Realm', 'http://62.217.120.158:4000/', 'vagoskar', 'mypass')
#        opener = urllib2.build_opener(proxy_handler, proxy_auth_handler)
#        # This time, rather than install the OpenerDirector, we use it directly:
#        resp = opener.open('http://62.217.120.158:4000/')
#        urllib2.install_opener(opener)
#        req = urllib2.Request('http://62.217.120.158:4000/?action=create&size=10G&access=private')
#        req = urllib2.Request('http://62.217.120.158:4000/?action=destroy&volume_id=vol-2')
#        req = urllib2.Request('http://62.217.120.158:4000/?action=list')
#        req = urllib2.Request('http://62.217.120.158:4000/?action=attach&instance=44&device=vda&volume=vol-1')
#        response = urllib2.urlopen(req, timeout=30)
#        print response.read()               
#        opener.close()

    def connect(self, user, passwd, endpoint, port):
        proxy_handler = urllib2.ProxyDigestAuthHandler()
        proxy_auth_handler = urllib2.HTTPDigestAuthHandler()
        proxy_auth_handler.add_password('StratusLab Realm', 'http://'+endpoint+':'+port+'/', user, passwd)
        self.opener = urllib2.build_opener(proxy_handler, proxy_auth_handler)
        # This time, rather than install the OpenerDirector, we use it directly:
        resp = self.opener.open('http://'+endpoint+':'+port+'/')
        urllib2.install_opener(self.opener)
        return resp

    def main(self):
        parser = argparse.ArgumentParser(description='StratusLab Volume Management.')
        parser.add_argument('action', type=str, choices=['create', 'delete', 'list', 'attach', 'detach'], 
                            action="store", help='Define the action and provide parameters')
        parser.add_argument('volume_id', type=str, nargs='?',
                           help='A volume id (optional for create, list)')
        parser.add_argument('-s', '--size', dest="size",action="store", default="", help='The size of the volume that will be created.')
        parser.add_argument('-a', '--access', dest="access",action="store", default="private", help='Access restrictions for the new volume. (public or private)')
        parser.add_argument('-i', '--instance', dest="instance",action="store", default="", help='The instance to attach a volume to.')
        parser.add_argument('-d', '--device', dest="device",action="store", default="", help='The device on which the volume will be available (e.g. vda to have the volume available at /dev/vda).')
        parser.add_argument('-u', '--username', dest="user",action="store", default="", help='Your username or certificate common name.')
        parser.add_argument('-p', '--password', dest="passwd",action="store", default="", help='Your password')
        parser.add_argument('-e', '--endpoint', dest="endpoint",action="store", default="", help='The cloud endpoint.')
        parser.add_argument('-P', '--port', dest="port",action="store", default="4000", help='The cloud endpoint port. (default 4000)')
        self.args = parser.parse_args()

        if self.args.action == 'create':
            self.connect(self.args.user, self.args.passwd, self.args.endpoint, self.args.port)
            req = urllib2.Request('http://'+self.args.endpoint+':'+self.args.port+'/'+'/?action=create&size='+self.args.size+'&access='+self.args.access)
            response = urllib2.urlopen(req, timeout=30)
            print response.read()
            self.opener.close()
        elif self.args.action == 'delete':
            self.connect(self.args.user, self.args.passwd, self.args.endpoint, self.args.port)
            req = urllib2.Request('http://'+self.args.endpoint+':'+self.args.port+'/'+'/?action=destroy&volume_id='+self.args.volume_id)
            response = urllib2.urlopen(req, timeout=30)
            print response.read()
            self.opener.close()
        elif self.args.action == 'list':
            self.connect(self.args.user, self.args.passwd, self.args.endpoint, self.args.port)
            req = urllib2.Request('http://'+self.args.endpoint+':'+self.args.port+'/'+'/?action=list')
            response = urllib2.urlopen(req, timeout=30)
            print response.read()
            self.opener.close()
        elif self.args.action == 'attach':
            self.connect(self.args.user, self.args.passwd, self.args.endpoint, self.args.port)
            req = urllib2.Request('http://'+self.args.endpoint+':'+self.args.port+'/'+'/?action=attach&instance='+self.args.instance+'&device='+self.args.device+'&volume_id='+self.args.volume_id)
            response = urllib2.urlopen(req, timeout=30)
            print response.read()
            self.opener.close()
        elif self.args.action == 'detach':
            self.connect(self.args.user, self.args.passwd, self.args.endpoint, self.args.port)
            req = urllib2.Request('http://'+self.args.endpoint+':'+self.args.port+'/'+'/?action=detach&volume_id='+self.args.volume_id)
            response = urllib2.urlopen(req, timeout=30)
            print response.read()
            self.opener.close()
            
        
if __name__ == '__main__':
    client = NFSClient()
    client.main()
#    client.connect()