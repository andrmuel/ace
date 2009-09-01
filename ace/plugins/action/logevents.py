#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
A very simlpe action plugin to log events to syslog.
"""

from ace.plugins.action.base import ActionPlugin
import syslog

class EventLogger(ActionPlugin):
	"""
	Logs events to syslog.
	"""
	def executeAction(self, events):
		"""
		Logs the events to syslog (facility: LOG_INFO)
		"""
		for event in events:
			syslog.syslog(syslog.LOG_INFO, "Event from EventLogger: "+str(event))
