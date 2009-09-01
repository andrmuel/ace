#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest

from ace import event
from ace.util.exceptions import *

class TestEvent(unittest.TestCase):
	"""
	Unit test for the event class and the event generator
	"""
	
	def testIncompleteException(self):
		"""
		incomplete information must raise an exception
		"""
		self.assertRaises(IncompleteEventInformationException, event.Event, name="TEST")
		self.assertRaises(IncompleteEventInformationException, event.Event, host="TEST")

	def testUnknownFieldException(self):
		"""
		an unknown event field (invalid function parameter) must raise an exception
		"""
		self.assertRaises(UnknownEventFieldException, event.Event, foo="bar")
	
	def testUnknownStatusException(self):
		"""
		an invalid status must raise an exception
		"""
		self.assertRaises(UnknownEventStatusException, event.Event, name="TEST", host="host1", status="foo")
	
	def testUnknownTypeException(self):
		"""
		an invalid type must raise an exception
		"""
		self.assertRaises(UnknownEventTypeException, event.Event, name="TEST", host="host1", type="foo")
	
	def testEventIDGeneration(self):
		"""
		different IDs must be generated even if two events with the same
		parameters are generated shortly after each other
		"""
		e1 = event.Event(name="TEST", host="host-1")
		e2 = event.Event(name="TEST", host="host-1")
		self.assertNotEqual(e1.id, e2.id)

	def testRandomEventGenerator(self):
		"""
		random events should be generated without any problems, and they should
		all have different IDs		
		"""
		g = event.EventGenerator()
		events = g.randomEvents(1000)
		ids = [e.id for e in events]
		self.assert_(len(set(ids))==1000)

if __name__ == '__main__':
	unittest.main()

