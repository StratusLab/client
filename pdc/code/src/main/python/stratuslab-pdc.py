#!/usr/bin/python

import sys
sys.path.append('/var/lib/stratuslab/python')

from daemon import runner
from stratuslab_pdc.controller import Controller

controller = Controller()
r = runner.DaemonRunner(controller)
r.do_action()
