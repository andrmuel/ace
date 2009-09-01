#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Checks the return value of a script.

This plugin is mostly for demonstration purposes, and could be implemented
better, with more safety checks.
"""

import os
from ace.plugins.condition.base import ConditionPlugin

class ScriptReturnValue(ConditionPlugin):
	"""
	A plugin to check the return value of an external script or application.

	Parameters:
	 - script: the name of the script
	 - retval: the expected return value 
	"""
	def __init__(self, config, logger, parameters, number_of_queries):
		"""
		@param parameters: a dictionary with a parameter script, which
		should contain the name of a script, a paramater retval, which
		specifies the expected return value, and an optional parameter args,
		which specifies arguments for the script.
		"""
		ConditionPlugin.__init__(self, config, logger, parameters, number_of_queries)
		if not number_of_queries == 0:
			self.raiseException("ScriptReturnValue", "Plugin does not take any input events.")
		if not parameters.has_key("script"):
			self.raiseException("ScriptReturnValue", "Plugin needs parameter 'script'.")
		if not parameters.has_key("retval"):
			self.raiseException("ScriptReturnValue", "Plugin needs parameter 'retval'.")
		if not parameters["retval"].isdigit():
			self.raiseException("ScriptReturnValue", "Plugin parameter 'retval' should be an integer.")
		self.script = parameters['script']
		self.retval = int(parameters['retval'])
		if parameters.has_key('args'):
			self.args = parameters['args']
		else:
			self.args = ""
	
	def checkCondition(self, trigger=None, events=None):
		"""
		@return: returs true, if the script returns with an exit value as
		specified
		"""
		return (self.retval == os.system(self.script+" "+self.args))


