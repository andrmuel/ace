#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with base class for sources.
"""

import threading
import time
from ace.translators import input as input_translators
from ace.util.exceptions import IOSourceException

class Source(threading.Thread):
	"""
	This class provides a base class for sources.
	"""
	def __init__(self, num, config, logger, queue):
		"""
		Init function - may be overwritten, but the parent should usually be called.
		
		@param num: identification number of this source
		@type  num: int
		@param config: instance of the Configuration class
		@param logger: instance of the Logger class
		@param queue: the input queue
		"""
		# parent
		threading.Thread.__init__(self)
		# params
		self.num = num
		self.config = config
		self.logger = logger
		self.queue = queue
		# name/options from config
		(self.name, self.options) = config.splitLine(config.input[num]['source'])
		# log
		self.logger.logInfo("Source: Source %d (%s): init." % (self.num, self.name))
		# internal variables
		self.stop_processing = False
		# translator
		self.translator_name = config.input[num]['translator'].split(':')[0]
		self.Translator = input_translators.get_translator(self.translator_name)
		self.translator = self.Translator(num, config, logger)

	def raiseException(self, problem):
		"""
		Generates an IOSourceException.
		
		@param problem: problem description
		"""
		raise IOSourceException(self.num, self.name, problem)

	def finish(self):
		"""
		Finish processing and stop the thread.
		"""
		self.stop_processing = True
		self.logger.logDebug("Source "+str(self.num)+": finishing.")
		if self.config.simulation:
			self.cleanup()

	def cleanup(self):
		"""
		Cleanup function - can (but doesn't have to be) overwritten to clean up
		after processing.
		"""
		pass

	def run(self):
		"""
		The main thread function - ideally, this function should not have to be
		overwritten.
		"""
		while not self.stop_processing:
			self.work()
			time.sleep(self.config.thread_sleep_time)
		self.cleanup()
		self.logger.logDebug("Source %d: thread done." % self.num)

	def work(self):
		"""
		The work function, which is called by the run function. This function
		does the work of one step.
		
		This function must be implemented by the derived class.
		"""
		raise NotImplementedError

