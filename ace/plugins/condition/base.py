#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with base class for condition plugins.
"""

from ace.util.exceptions import PluginException

class ConditionPlugin:
	"""
	Base class for condition plugins.
	"""

	def __init__(self, config, logger, parameters, number_of_queries):
		"""
		Constructor - may be extended. The derived instance should raise a
		PluginException, if there are any errors.
		
		@param config: configuration instance
		@param logger: logger instance
		@param parameters: plugin parameters
		@type  parameters: dict()
		"""
		self.config = config
		self.logger = logger
		self.parameters = parameters

	def checkCondition(self, trigger, events):
		"""
		Method, which is called to evaluate the plugin. This method must be
		overwritten by the derived class.
		
		@param trigger: rule trigger events (should not be modified)
		@type  trigger: Event
		@param events: input events (events should not be modified)
		@type  events: a list with zero or more lists with zero or more Event's
		"""
		raise NotImplementedError

	def raiseException(self, name, problem):
		"""
		Raises a PluginException.
		"""
		raise PluginException("ConditionPlugin", name, problem)
