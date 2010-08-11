auto %(bridge)s
iface %(bridge)s inet dhcp
pre-up ifconfig %(iface)s down
pre-up brctl addbr %(bridge)s
pre-up brctl addif %(bridge)s %(iface)s
pre-up ifconfig %(iface)s 0.0.0.0
post-down ifconfig %(iface)s down
post-down ifconfig %(bridge)s down
post-down brctl delif %(bridge)s %(iface)s
post-down brctl delbr %(bridge)s