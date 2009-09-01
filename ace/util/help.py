#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with Help class.
"""

class Help:
	"""
	Simple help class, which prints some infos, if the user enters 'help' in
	the interactive mode.
	"""
	def __init__(self):
		pass
	def __repr__(self):
		return """This is the Python console started by ace. It lets you interact with any part
of the code, by using normal Python statements.

Usage examples:

 - get some statistics (requires the RPC server):

   self.rpchandler.getStats()

 - get a list with the name of each event in the cache

   [event.getName() for event in self.core.cache.events] 

 - print an event with a specific ID from the cache:

   print self.core.cache.getEventByID("e9294e806d02fd8ebd90e345434c16a3")

 - trigger a cache cleanup at the end of the current timestep

   self.core.triggerClearCache()

 - cleanup the cache immediately (potentially harmful)

   self.core.cache.clearCache()

 - get the number of sinks

   len(self.sinks)

 - check, whether the thread of sink 0 is alive:

   self.sinks[0].isAlive()"""
