#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
A plugin to specify a condition on the current weekday.
"""

import datetime
from ace.plugins.condition.base import ConditionPlugin

class Weekday(ConditionPlugin):
	"""
	A plugin to specify a condition on the current weekday.

	Parameters:
	 - days: a comma separated list of weekdays, specified either as int
	   (starting with 0 on monday, ending with 6 on sunday) or as abbreviated
	   day name (mon, tue, wed, thu, fri, sat, sun; not case sensitive)
	"""

	weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

	def __init__(self, config, logger, parameters, number_of_queries):
		ConditionPlugin.__init__(self, config, logger, parameters, number_of_queries)
		if not number_of_queries == 0:
			self.raiseException("Weekday", "Plugin does not take any input events.")
		if not parameters.has_key("days"):
			self.raiseException("Weekday", "Plugin needs parameter 'days'.")
		self.days_ok = []
		for day in parameters['days'].split(','):
			if day == '':
				continue
			elif day.isdigit():
				self.days_ok.append(int(day))
			elif day.lower() in self.weekdays:
				self.days_ok.append(self.weekdays.index(day.lower()))
			else:
				self.raiseException("Weekday", "'%s' is not a valid weekday." % day)

	def checkCondition(self, trigger=None, events=None):
		"""
		Checks, whether the current day is one of the given days.
		"""
		day = datetime.datetime.now().weekday()
		if day in self.days_ok:
			return True
		else:
			return False
