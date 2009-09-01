#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Ticker source module.
"""

import time
from ace.io.sources.base import Source
from ace.event import Event

class TickerSource(Source):
	"""
	Ticker source.

	Generates events in a regular interval.

	Configuration options:
	 - interval: interval in seconds
	 - eventname: name of the generated events
	"""
	def __init__(self, num, config, logger, queue):
		Source.__init__(self, num, config, logger, queue)
		if self.options.has_key("eventname"):
			self.eventname = self.options['eventname']
		else:
			self.raiseException("No 'eventname' specified in options.")
		if not self.options.has_key("interval"):
			self.raiseException("No 'interval' specified in options.")
		if not self.options['interval'].isdigit():
			self.raiseException("Option 'interval': must be a number.")
		self.interval = int(self.options['interval'])


	def run(self):
		"""
		Redefined main thread function - always sleeps as long as specified in
		'interval'.
		"""
		while not self.stop_processing:
			self.work()
			time.sleep(self.interval)
		self.logger.logDebug("Source "+str(self.num)+": thread done.")

	def work(self):
		"""
		Generates one event.
		"""
		self.queue.put(Event(name=self.eventname, host=self.config.hostname))

