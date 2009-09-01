#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides a function for runtime plugin loading.
"""

from ace.util.exceptions import PluginNotFoundException

# all plugins must be imported here
from ace.plugins.condition.weekday import Weekday
from ace.plugins.condition.script_return_value import ScriptReturnValue

# class must be added here (key is the plugin name)
PLUGINS = {
		'weekday': Weekday,
		'script_return_value': ScriptReturnValue
	}

def get_plugin(plugin):
	"""
	Returns the class for the specified condition plugin.
	"""
	if not PLUGINS.has_key(plugin):
		raise PluginNotFoundException("condition", plugin)
	else:
		return PLUGINS[plugin]
