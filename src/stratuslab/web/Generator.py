#!/usr/bin/python

import cgi, cgitb
cgitb.enable()

from stratuslab.Monitor import Monitor
import stratuslab.Util as Util

class HtmlGenerator(object):
    
    def __init__(self):
        self.template = None
        self.monitor = None
        self.title = ''
        self.fields = []
        self.fieldTemplate = '            <td>%(value)s</td>\n'
        self.metaRefresh = '<meta http-equiv="refresh" content="%(refreshInSeconds)s">'
        self.autoRefreshLink = '<a href="%(query)s">%(enableDisable)s auto refresh</a>'
        
    def run(self):
        configFile = 'conf/stratuslab.cfg'
        config = Util.parseConfig(configFile)
        options = {'configFile': configFile,
                   'password': 'oneadmin'}
        self.monitor = Monitor(options, config)
        content = self._generate()
        self._serialize(content)
        
    def _generate(self):
        templateTokens = {'headTitle': 'StratusLab Monitor',
                          'title': self.title}
        templateTokens = self._setRefresh(templateTokens)
        templateTokens['fieldsHeader'] = self._generateHeader()
        templateTokens['list'] = self._generateFieldsContent()
        content = self.template % templateTokens
        return content
        
    def _setRefresh(self, templateTokens):
        refresh = self._getRefreshQueryValue()
        if refresh:
            templateTokens['meta'] = self.metaRefresh % {'refreshInSeconds': refresh}
            autoRefreshTokens = {'query': self._getQuery(),
                                 'enableDisable': 'Disable'}
        else:
            templateTokens['meta'] = ''
            autoRefreshTokens = {'query': self._getQuery(),
                                 'enableDisable': 'Enable'}

        templateTokens['autoRefreshLink'] = self.autoRefreshLink % autoRefreshTokens
        return templateTokens

    def _getQuery(self):
        id = self._getId()
        mustRefresh = not self._getRefreshQueryValue()
        if id and mustRefresh:
            return '?id=%s&refresh=5' % id
        if id:
            return '?id=%s' % id
        if mustRefresh:
            return '?refresh=5'
        return '?'

    def _getRefreshQueryValue(self):
        return self._getQueryValue('refresh')

    def _getData(self):
        return []

    def _generateHeader(self):
        fieldTpl = '            <th>%s</th>\n'
        content = ''
        for field in self.fields:
            content += fieldTpl % self.fields[field]
        return '        <tr>\n' + content + '        </tr>'

    def _generateFieldsContent(self):
        content = ''
        for info in self._getData():
            content += '        <tr>\n'
            for field in self.fields:
                value = self._getFieldValue(field, info)
                content += self._generateSingleFieldContent(self.fields[field], value)
            content += '        </tr>\n'
        return content
            
    def _getFieldValue(self, key, info):
        if key == 'state':
            return self._getState(info)
        return info.attribs.get(key,'')
    
    def _getState(self, info):
        pass
    
    def _generateSingleFieldContent(self, key, value, template=None):
        if template:
            _template = template
        else:
            _template = self.fieldTemplate
        return _template % {'key': key, 'value': value}

    def _serialize(self, content):
        print 'Content-type: text/html\n'
        print content

    def _getId(self):
        return self._getQueryValue('id')

    def _getQueryValue(self, key):
        form = cgi.FieldStorage()
        if key in form:
            return form[key].value
        else:
            return None

class ListGenerator(HtmlGenerator):

    def __init__(self):
        super(ListGenerator,self).__init__()
        self.template = open('list.html.tpl').read()
        self.idTemplate = ''

    def _generateSingleFieldContent(self, key, value, template=None):
        if key.lower() == 'id':
            _template = self.idTemplate
        else:
            _template = self.fieldTemplate
        return super(ListGenerator,self)._generateSingleFieldContent(key, value, _template)


class DetailedGenerator(HtmlGenerator):

    def __init__(self):
        super(DetailedGenerator,self).__init__()
        self.template = open('detail.html.tpl').read()
        self.fieldTemplate = '        <tr>\n          <td>%(key)s</td><td>%(value)s</td>\n        </tr>\n'
        self.fieldGroups = {}

    def _generateHeader(self):
        return ''

    def _generateFieldsContent(self):
        content = ''
        info = self._getData()[0]
        for groupName in self.fieldGroups:
            content += '    <h3>%s</h3>\n' % groupName
            content += '    <table>\n'
            content += self._generateGroupListContent(groupName, info)
            content += '    </table>\n'
        return content

    def _generateGroupListContent(self, groupName, info):
        content = ''
        for field in self.fieldGroups[groupName]:
            value = self._getFieldValue(field, info)
            content += self._generateSingleFieldContent(self.fieldGroups[groupName][field], value)
        return content
