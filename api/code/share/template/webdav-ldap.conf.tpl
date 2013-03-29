Alias /images "%(imageDir)s/eu/stratuslab/appliances"

%(ldapSSL)s
  <Directory "%(imageDir)s">
        Dav On
        Options +Indexes
        IndexOptions FancyIndexing
        AddDefaultCharset UTF-8
        AuthType Basic
        AuthName "Image Repository Access"
        AuthLDAPURL "%(ldapURL)s"
        AuthBasicProvider ldap
        AuthzLDAPAuthoritative off
        AuthLDAPBindDN "%(ldapBind)s"
        AuthLDAPBindPassword %(ldapPasswd)s
        <Limit PUT POST DELETE PROPPATCH MKCOL COPY MOVE LOCK UNLOCK>
                Require valid-user
        </Limit>
        Order allow,deny
        Allow from all
    </Directory>
