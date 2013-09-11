#!/usr/bin/python

from daemon import runner
from stratuslab_vmc.controller import Controller

controller = Controller()
r = runner.DaemonRunner(controller)
r.do_action()
