#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides a function to dynamically load an action plugin.
"""

from ace.util.exceptions import PluginNotFoundException

# all plugins must be imported here
from ace.plugins.action.logevents import EventLogger
from ace.plugins.action.mailevents import MailAction
from ace.plugins.action.enrich_masterslave import EnrichMasterSlave
from ace.plugins.action.enrich_regexp import EnrichRegexp

# class must be added here (key is the plugin name)
PLUGINS = {
		'logevents': EventLogger,
		'mailevents': MailAction,
		'enrich_masterslave': EnrichMasterSlave,
		'enrich_regexp': EnrichRegexp
	}

def get_plugin(plugin):
	"""
	Returns the class for the specified plugin.
	"""
	if not PLUGINS.has_key(plugin):
		raise PluginNotFoundException("action", plugin)
	else:
		return PLUGINS[plugin]
