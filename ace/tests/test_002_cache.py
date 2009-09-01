#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest
import types
from ace import event, contexts, cache, rulebase
from ace.util.exceptions import *
from ace.util import configuration, logging
from ace.basisfunctions import rulecomponents

class TestEventHandler:
	"""
	Test EventHandler, to see which events would be forwarded ..
	"""
	def __init__(self):
		self.events = []
	
	def generateOutputEvent(self, event):
		self.events.append(event)

class TestCache(unittest.TestCase):
	"""
	Unittest for event cache Class.
	"""
	
	def setUp(self):
		self.config = configuration.Config()
		self.logger = logging.Logger(self.config)
		self.evgen = event.EventGenerator()
		self.ticker = None
		self.cache = cache.EventCache(self.config, self.logger, self.ticker)
		self.cm = contexts.ContextManager(self.config, self.logger, self.ticker, self.cache)
		self.eh = TestEventHandler()

	def testDrop(self):
		events = self.evgen.randomEvents(20)
		self.cache.addEvents(events)
		dropfunc = rulecomponents.drop
		self.assert_(len(self.cache.events)==20)
		drop = [events[10],events[11]]
		dropfunc(cache=self.cache, selected_events=drop)
		self.assert_(len(self.cache.events)==18)
		self.assert_(events[9] in self.cache.getEvents())
		self.assert_(events[10] not in self.cache.getEvents())
		self.assert_(events[11] not in self.cache.getEvents())
		self.assert_(events[12] in self.cache.getEvents())

	def testForward(self):
		events = self.evgen.randomEvents(20)
		events[1].forwarded = True
		self.cache.addEvents(events)
		# events2 = self.evgen.randomEvents(20)
		# forward_events = events[0:10]+events2[0:10]
		forward_events = events[0:10]
		forwardfunc = rulecomponents.forward
		forwardfunc(cache=self.cache, selected_events=forward_events, core=self.eh)
		self.assert_(len(self.eh.events)==9)
		self.assert_(events[0] in self.eh.events)
		self.assert_(events[1] not in self.eh.events) # was already forwarded
		# self.assert_(events2[0] not in self.eh.events) # not in cache

if __name__ == '__main__':
	unittest.main()

