#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with base class for sinks.
"""

import threading
import time
from ace.translators import output as output_translators
from ace.util.exceptions import IOSinkException

class Sink(threading.Thread):
	"""
	This class can be used as a base class for sinks.
	"""
	def __init__(self, num, config, logger, queue):
		"""
		Init function - may be overwritten, but the parent should usually be called.
		
		@param num: identification number of this sink
		@type  num: int
		@param config: instance of the Configuration class
		@param logger: instance of the Logger class
		@param queue: the output queue
		"""
		# parent
		threading.Thread.__init__(self)
		# params
		self.num = num
		self.config = config
		self.logger = logger
		self.queue = queue
		# name/options from config
		(self.name, self.options) = config.splitLine(config.output[num]['sink'])
		# log
		self.logger.logInfo("Sink: Sink %d (%s) init." % (self.num, self.name))
		# internal variables
		self.stop_processing = False
		# translator
		self.translator_name = config.output[num]['translator'].split(':')[0]
		self.Translator = output_translators.get_translator(self.translator_name)
		self.translator = self.Translator(num, config, logger)

	def raiseException(self, problem):
		"""
		Generates an IOSinkException with the given problem description.
		
		@param problem: string describing the problem
		"""
		raise IOSinkException(self.num, self.name, problem)

	def finish(self):
		"""
		Finish processing and stop the thread.
		"""
		self.stop_processing = True
		self.logger.logDebug("Sink "+str(self.num)+": finishing.")

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
		self.writeOutput(self.translator.getHeader())
		while not self.stop_processing:
			self.work()
			time.sleep(self.config.thread_sleep_time)
		self.writeOutput(self.translator.getFooter())
		self.cleanup()
		self.logger.logDebug("Sink %d: thread done." % self.num)

	def work(self):
		"""
		The work function is called repeatedly by the run function, to process
		events from the queue.
		"""
		while self.queue.qsize()>0 and not self.stop_processing:
			self.processEvent(self.queue.get())
			self.queue.task_done()

	def processEvent(self, event):
		"""
		This function is called repeatedly by the work function, and should
		process one event, each time it is called.
		
		This function must be overwritten.

		@param event: an event from the queue
		"""
		raise NotImplementedError

	def writeOutput(self, data):
		"""
		Should be overwritten with a method that writes the data to the output.
		@param data:  a string with output data
		"""
		raise NotImplementedError
