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

class TestScriptRetvalConditionPlugin(unittest.TestCase):
	"""
	Unittest for script_return_value plugin.
	"""
	
	def setUp(self):
		self.script_plugin = condition_plugins.get_plugin("script_return_value")

	def testRaisePluginException(self):
		self.assertRaises(PluginException, self.script_plugin, None, None, parameters={'script': 'true', 'retval': '0', 'args':"foo"}, number_of_queries=2) # too many queries
		self.assertRaises(PluginException, self.script_plugin, None, None, parameters={'script': 'true', 'retval': 'a', 'args':"foo"}, number_of_queries=0) # retval not int
		self.assertRaises(PluginException, self.script_plugin, None, None, parameters={'script': 'true'}, number_of_queries=0) # no retval
		self.assertRaises(PluginException, self.script_plugin, None, None, parameters={'retval': '0', 'args':"foo"}, number_of_queries=0) # no script

	def testRet0(self):
		plugin = self.script_plugin(None, None, parameters={'script': 'true', 'retval': '0', 'args':"foo"}, number_of_queries=0)
		self.assertTrue(plugin.checkCondition())
		
	def testRetNot0(self):
		plugin = self.script_plugin(None, None, parameters={'script': 'false', 'retval': '0'}, number_of_queries=0)
		self.assertFalse(plugin.checkCondition())

if __name__ == '__main__':
	unittest.main()

