'''
Created on Jul 5, 2011

@author: vagos
'''
import nfsstore
from werkzeug.wrappers import Request, Response
import authdigest, logging
from logging import handlers
import utils, commands


class Server():
    
    def __init__(self):
        self.utils = utils.Utils()
        self.authDB = authdigest.RealmDigestDB('StratusLab Realm')
        self.store = nfsstore.NFSStore()
        ## Install logger
        LOG_FILENAME = self.utils.store_dir+'/logs/nfsstore.log'
        self.my_logger = logging.getLogger('Server')
        self.my_logger.setLevel(logging.DEBUG)
        
        loghandler = handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        loghandler.setFormatter(formatter)
        self.my_logger.addHandler(loghandler)
    
    def read_passwords(self, loginfile):
        f = open(loginfile,'r')
        for line in f:
            if line.startswith('#') or line.startswith('\n') :
                continue
            if line.startswith('\"CN'):
                user = line.split('\"')[1]
                self.authDB.add_user(user,'')
            else:
                userpass = line.split(',')[0]
                userpass =  userpass.split('=')
                self.authDB.add_user(userpass[0],userpass[1] )
#                self.my_logger.debug(userpass[0]+" " + userpass[1])

    @Request.application
    def application(self, request):
        if not self.authDB.isAuthenticated(request):
            return self.authDB.challenge()
        session={}
        session['user'] = request.authorization.username
        for i in request.values:
            print i, "=", request.values[i]

        allvalues = {}
        allvalues.update(request.values.to_dict())
        allvalues.update( session)
        print allvalues
        
        responseData = ""
        
        if request.values.has_key('action'):
            if allvalues['action'] == "create":
                responseData = self.store.create(allvalues)
            elif allvalues['action'] == "attach":
                responseData = self.store.attach(allvalues)
            elif allvalues['action'] == "detach":
                responseData = self.store.detach(allvalues)
            elif allvalues['action'] == "destroy":
                responseData = self.store.destroy(allvalues)
            elif allvalues['action'] == "share":
                responseData = self.store.share(allvalues)
            elif allvalues['action'] == "list":
                responseData = self.store.list(allvalues)
            elif allvalues['action'] == "show":
                responseData = self.store.show(allvalues)
            else:
                return Response('Action not supported!!!')
        
        return Response(responseData)

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    server = Server()
    server.read_passwords("/etc/stratuslab/one-proxy/login-pswd.properties")
    server.read_passwords("/etc/stratuslab/one-proxy/login-cert.properties")
    run_simple(server.utils.ip, int(server.utils.port), server.application)