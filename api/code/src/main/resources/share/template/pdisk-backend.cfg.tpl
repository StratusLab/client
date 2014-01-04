[main]
log_file =

# Comma separated list of backend servers
iscsi_proxies = %(persistentDiskBackendSectionsNames)s
mgt_user_name = %(persistentDiskBackendMgtUserName)s
mgt_user_private_key = %(persistentDiskBackendMgtUserPrivateKey)s

# Sections for pdisk-backend.cfg config file
# These are active if set in the configuration
# parameter disk.backend.sections.names
%(persistentDiskBackendSections)s
