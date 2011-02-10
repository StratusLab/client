:database: sqlite://auth.db
:authentication: simple
:quota:
  :enabled: true
  :defaults:
    :cpu: %(quotaCpu)s
    :memory: %(quotaMemory)