#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with base class for input translators.
"""

from ace.util.exceptions import InputTranslatorException

class InputTranslator:
	"""
	Base class for input translators.
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
		(self.name, self.options) = config.splitLine(config.input[num]['translator'])
		# log
		self.logger.logInfo("Input translator number "+str(self.num)+" ("+self.name+") init.")

	def translate(self, inputdata):
		"""
		This function should be overwritten with a function, that translates
		input data into events.
		
		@param inputdata: string with input data
		@return: an event generator
		"""
		raise NotImplementedError

	def raiseException(self, problem):
		"""
		Generates an InputTranslatorException with the current translator
		number and name, and the given problem description.
		"""
		raise InputTranslatorException(self.num, self.name, problem)
