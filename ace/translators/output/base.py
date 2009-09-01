#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with base class for output translators.
"""

from ace.util.exceptions import OutputTranslatorException

class OutputTranslator:
	"""
	Base class for output translators.
	"""
	def __init__(self, num, config, logger):
		"""
		Init - may be overwritten, but parent should be called.
		
		@param num: number of this translator
		@param config: config instance
		@param logger: logger instance
		"""
		# params
		self.num = num
		self.config = config
		self.logger = logger
		# name/options from config
		(self.name, self.options) = config.splitLine(config.output[num]['translator'])
		# log
		self.logger.logInfo("Output translator number "+str(self.num)+" ("+self.name+") init.")

	def translate(self, event):
		"""
		This function should be overwritten with a function, that translates
		an event into output data.
		
		@param event: event to translate
		@return: a string representing the event
		"""
		raise NotImplementedError
	
	def raiseException(self, problem):
		"""
		Raises an OutputTranslatorException with the given problem description.
		"""
		raise OutputTranslatorException(self.num, self.name, problem)

	def getHeader(self):
		"""
		May be overwritten to return a header string.
		"""
		return ""

	def getFooter(self):
		"""
		May be overwritten to return a footer string.
		"""
		return ""
