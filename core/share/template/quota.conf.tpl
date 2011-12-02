# Database URI
:db: mysql://%(oneDbUsername)s:%(oneDbPassword)s@%(oneDbHost)s/opennebula

#-------------------------------------------------------------------------------
# Default quotas, these apply to all users. Leave empty to disable quota for 
# a given metric.
#-------------------------------------------------------------------------------
:defaults:
  :cpu: %(quotaCpu)s
  :memory: %(quotaMemoryKB)s
  :num_vms:
  :storage:
