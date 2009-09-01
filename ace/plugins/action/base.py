#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with base class for action plugins.
"""

from ace.util.exceptions import PluginException

class ActionPlugin:
	"""
	Base class for action plugins.
	"""

	def __init__(self, config, logger, parameters):
		"""
		Contstructor - may be extended. The derived instance should raise a
		PluginException, if there are any errors.
		
		@param config: configuration instance
		@param logger: logger instance
		@param parameters: plugin parameters
		@type  parameters: dict()
		"""
		self.config = config
		self.logger = logger
		self.parameters = parameters

	def executeAction(self, events):
		"""
		Method, which is called to execute the plugin. This method must be
		overwritten by the derived class.
		
		@param events: input events (events may be modified)
		@type  events: a list with zero or more lists with zero or more Event's
		"""
		raise NotImplementedError

	def raiseException(self, name, problem):
		"""
		Generates a PluginException.
		"""
		raise PluginException("ActionPlugin", name, problem)
