#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Demo plugin to enrich events with information about master and slave of a
cluster.

Currently, we just infer from the host name; in a real-world setup, this plugin
would likely have to read the info from a database.
"""

from ace.plugins.action.base import ActionPlugin

class EnrichMasterSlave(ActionPlugin):
	"""
	Enriches event with master/slave hostname.
	"""

	def executeAction(self, events):
		"""
		Enriches the events.
		"""
		for event in events:
			host = event.getHost()
			if host.endswith("-1") or host.endswith("-2"):
				master = host[:-2]+"-1"
				slave = host[:-2]+"-2"
				event.setAttribute("master", master)
				event.setAttribute("slave", slave)
