#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Ticker module - contains the ticker class.
"""

import time

class Ticker:
	"""
	Time base for the correlation engine.
	"""
	def __init__(self, config, logger):
		# log
		logger.logInfo("Ticker: init.")
		# parameters
		self.config = config
		self.logger = logger
		# etc
		if self.config.realtime:
			self.firsttick = int(time.time())
		else:
			self.firsttick = 0
		self.tick = self.firsttick
		self.starttime = int(time.time())

	def getTimeRunning(self):
		return time.time()-self.starttime

	def getTimeRunningString(self):
		t = int(self.getTimeRunning())
		return "%d days, %02d:%02d:%02d" % (t//(3600*24), (t//3600)%24, (t//60)%60, t%60)

	def getTick(self):
		return self.tick

	def getTime(self):
		return int(time.time())

	def advance(self):
		"""
		Advances the ticker to the next tick. Important: if config.realtime is
		True, the ticker sleeps, until the system time has reached a second
		count higher than the current tick.
		"""
		# for real-time, wait until actual time is > CE time, before advancing the time step
		if self.config.realtime:
			while self.tick >= int(time.time()):
				time.sleep(self.config.thread_sleep_time)
		self.tick += 1
		self.logger.logDebug("Tick advanced to %d." % self.tick)
		return self.tick
