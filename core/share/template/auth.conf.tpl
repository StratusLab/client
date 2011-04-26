:database: mysql://%(oneDbUsername)s:%(oneDbPassword)s@%(oneDbHost)s/opennebula
:authentication: simple
:quota:
  :enabled: true
  :defaults:
    :cpu: %(quotaCpu)s
    :memory: %(quotaMemoryKB)s
