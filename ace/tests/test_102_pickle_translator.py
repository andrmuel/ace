#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest
import Queue
import os
import sys
import cProfile
import time

from ace.util import configuration, logging, constants
from ace.translators.input.pickle_translator import EventUnpickler
from ace.translators.output.pickle_translator import EventPickler
from ace import event

class TestPickleTranslator(unittest.TestCase):
	"""
	Unittest for XML input and output translators.
	"""
	
	def setUp(self):
		self.config = configuration.Config()
		self.config.simulation = True
		self.config.fast_exit = False
		self.logger = logging.Logger(self.config)

	def testRandomEvents(self):
		g = event.EventGenerator()
		out_trans = EventPickler(0, self.config, self.logger)
		in_trans = EventUnpickler(0, self.config, self.logger)
		events = g.randomEvents(1000)
		s = ""
		for e in events:
			s += out_trans.translate(e)
		events2 = []
		for e in in_trans.translate(s[:50]):
			events2.append(e)
		for e in in_trans.translate(s[50:100]):
			events2.append(e)
		for e in in_trans.translate(s[100:]):
			events2.append(e)
		self.assert_(len(events)==len(events2))
		for i in range(len(events)):
			events2[i].arrival = events[i].getArrivalTime()
			events2[i].delaytime = events[i].delaytime
			events2[i].cachetime = events[i].cachetime
			self.assert_(events[i].__dict__==events2[i].__dict__)

if __name__ == '__main__':
	unittest.main()
	# cProfile.run("unittest.main()")
