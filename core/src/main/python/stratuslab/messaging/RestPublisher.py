import json
import commands

from stratuslab.HttpClient import HttpClient

class _RestPublisherHttpClient(object):
    def __init__(self, configHolder):
        self.restEndpoints = '{}'
        configHolder.assign(self)
        self.resource = '%s/%s' % (self.msg_endpoint, self.msg_queue)
        self.httpClient = HttpClient(configHolder)
        self._assignCredentials()

    def _assignCredentials(self):
        endpts_creds = json.loads(self.restEndpoints)
        try:
            creds = endpts_creds[self.msg_endpoint]
        except KeyError:
            print 'WARNING: no matching credentials for ' + self.msg_endpoint
        else:
            self.httpClient.addCredentials(creds['username'], creds['password'])

    def send(self, message):
        self.httpClient.put(self.resource, message)

class _RestPublisherCurl(object):
    def __init__(self, configHolder):
        self.restEndpoints = '{}'
        self.username = ''
        self.password = ''
        configHolder.assign(self)
        self.resource = '%s/%s' % (self.msg_endpoint, self.msg_queue)
        self._assignCredentials()

    def _assignCredentials(self):
        endpts_creds = json.loads(self.restEndpoints)
        try:
            creds = endpts_creds[self.msg_endpoint]
        except KeyError:
            print 'WARNING: no matching credentials for ' + self.msg_endpoint
        else:
            self.username = creds['username']
            self.password = creds['password']

    def send(self, message):
        user = ''
        if self.username and self.password:
            user = '--user %s:%s' % (self.username, self.password)
        cmd = 'curl -d %s -X PUT %s %s' % (message, user, self.resource)
        rc, output = commands.getstatusoutput(cmd)
        if rc != 0 or ('Error' in output):
            raise Exception("Command : %s\nFailed with :\n%s" % (cmd, output))

# FIXME: RestPublisherHttpClient.send() fails at the moment
RestPublisher = _RestPublisherCurl
