#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest
from ace.plugins import condition as condition_plugins
from ace.util.exceptions import *

class TestWeekdayConditionPlugin(unittest.TestCase):
	"""
	Unittest for weekday plugin.
	"""
	
	def setUp(self):
		self.Weekday = condition_plugins.get_plugin('weekday')

	def testPluginNotFoundException(self):
		self.assertRaises(PluginNotFoundException, condition_plugins.get_plugin, "FOOBAR")

	def testPluginNoException(self):
		wday = self.Weekday(None, None, parameters={'days': "0"}, number_of_queries=0)

	def testPluginTooManyQueriesException(self):
		self.assertRaises(PluginException, self.Weekday, None, None, parameters={'days': "0"}, number_of_queries=1)

	def testNoDaysParamException(self):
		self.assertRaises(PluginException, self.Weekday, None, None, parameters={}, number_of_queries=0)

	def testInvalidDayException(self):
		self.assertRaises(PluginException, self.Weekday, None, None, parameters={'days': 'foo'}, number_of_queries=0)

	def testAllYes(self):
		all = self.Weekday(None, None, parameters={'days': "0,1,2,3,4,5,6"}, number_of_queries=0)
		self.assertTrue(all.checkCondition())

	def testAllYes2(self):
		all = self.Weekday(None, None, parameters={'days': "Mon,Tue,Wed,Thu,Fri,Sat,Sun"}, number_of_queries=0)
		self.assertTrue(all.checkCondition())

	def testNoneNo(self):
		none = self.Weekday(None, None, parameters={'days': ""}, number_of_queries=0)
		self.assertFalse(none.checkCondition())

if __name__ == '__main__':
	unittest.main()

