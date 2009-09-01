#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions

"""
Null sink module.
"""

from ace.io.sinks.base import Sink

class NullSink(Sink):
	"""
	Null sink.

	Discards all events.
	"""

	def processEvent(self, event):
		"""
		Ignores a single event.
		"""
		pass

	def writeOutput(self, data):
		"""
		Does nothing.
		"""
		pass
