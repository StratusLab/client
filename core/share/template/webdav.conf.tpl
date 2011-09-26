Alias /images "%(imageDir)s/eu/stratuslab/appliances"

  <Directory "%(imageDir)s">
        Dav On
        Options +Indexes
        IndexOptions FancyIndexing
        AddDefaultCharset UTF-8
        AuthType Basic
        AuthName "Image Repository Access"
        AuthUserFile %(passwd)s
        <Limit PUT POST DELETE PROPPATCH MKCOL COPY MOVE LOCK UNLOCK>
                Require valid-user
        </Limit>
        Order allow,deny
        Allow from all
    </Directory>
