#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Enrich with information from a regular expression.
"""

import re
from ace.plugins.action.base import ActionPlugin

class EnrichRegexp(ActionPlugin):
	"""
	Enriches event with info from regexp (the first group of the match).

	Parameters:
	 - source: source attribute (where the string to match on is taken from)
	 - target: target attribute (where the match is stored)
	 - regexp: the regular expression
	"""

	def __init__(self, config, logger, parameters):
		ActionPlugin.__init__(self, config, logger, parameters)
		if not "source" in parameters.keys():
			self.raiseException("EnrichRegexp", "Need parameter 'source'.")
		if not "target" in parameters.keys():
			self.raiseException("EnrichRegexp", "Need parameter 'target'.")
		if not "regexp" in parameters.keys():
			self.raiseException("EnrichRegexp", "Need parameter 'regexp'.")
		self.source = parameters['source']
		self.target = parameters['target']
		try:
			self.regexp = re.compile(parameters['regexp'])
		except re.error:
			self.raiseException("EnrichRegexp", "Error compiling regexp.")

	def executeAction(self, events):
		"""
		Enriches the events.
		"""
		for event in events:
			if event.hasAttribute(self.source):
				result = self.regexp.search(event.getAttribute(self.source))
				if result:
					if len(result.groups()) > 0:
						event.setAttribute(self.target, result.groups()[0])
