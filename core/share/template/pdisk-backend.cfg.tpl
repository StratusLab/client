[main]
log_file =

# Comma separated list of backend servers
iscsi_proxies = %(persistent_disk_backend_sections_names)s
mgt_user_name = root
mgt_user_private_key = /root/.ssh/id_rsa

# Sections for pdisk-backend.cfg config file
# These are active if set in the configuration
# parameter disk.backend.sections.names
%(persistent_disk_backend_sections)s