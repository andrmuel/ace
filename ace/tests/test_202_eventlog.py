#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest

from ace import event
from ace.util import logging, configuration
from ace.plugins import action as action_plugins
from ace.util.exceptions import *

class TestEventLoggerActionPlugin(unittest.TestCase):
	"""
	Unittest for EventLogger.
	"""
	
	def setUp(self):
		self.config = configuration.Config()
		self.logger = logging.Logger(self.config)
		EventLogger = action_plugins.get_plugin("logevents")
		self.eventlogger = EventLogger(None, None, None)
		self.evgen = event.EventGenerator()

	def testNonexistantPluginException(self):
		self.assertRaises(PluginNotFoundException, action_plugins.get_plugin, "FOOBAR")
	
	def testNoErrors(self):
		# can't really check much here, just that there are no errors, e.g.
		# after interface change (can't check syslog output, because where it
		# ends up depends on the host configuration)
		events = self.evgen.randomEvents(2)
		self.eventlogger.executeAction(events)
		

	def tearDown(self):
		self.logger.close()

if __name__ == '__main__':
	unittest.main()

