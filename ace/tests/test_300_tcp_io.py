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

from ace.util import configuration, logging
from ace.io.sources import TCPSource
from ace.io.sinks import TCPSink
from ace.translators.input import xml_translator as xmlinputtranslator
from ace.translators.output import xml_translator as xmloutputtranslator
from ace import event

class TestTCPIO(unittest.TestCase):
	"""
	Unittest for XML input and output translators.
	"""
	
	def setUp(self):
		self.queue = Queue.Queue(1000)
		# slight hack to determine the path of this module, so that the XML
		# files can always be loaded from the same path (the current path can't
		# be used, because it depends on how the test is executed):
		self.basedir = os.path.dirname(os.path.abspath(sys.modules[__name__].__file__))+"/"
		self.config = configuration.Config()
		self.config.simulation = False
		self.config.fast_exit = False
		self.config.events_dtd = self.basedir+"events.dtd"
		self.logger = logging.Logger(self.config)

	def testRandomEvents(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		inputqueue = Queue.Queue(1000)
		outputqueue = Queue.Queue(1000)
		for e in events:
			outputqueue.put(e)
		self.config.input = [{'source':"tcp:port=3003", 'translator':"xml"}]
		self.config.output = [{'sink':"tcp:host=localhost:port=3003", 'translator':"xml"}]
		source = TCPSource(0, self.config, self.logger, inputqueue)
		sink = TCPSink(0, self.config, self.logger, outputqueue)
		source.start()
		sink.start()
		outputqueue.join()
		sink.finish()
		sink.join()
		source.finish()
		source.join()
		self.assert_(outputqueue.qsize()==0)
		self.assert_(inputqueue.qsize()==100)
		self.assert_(events[0].id == inputqueue.queue[0].id)
		self.assert_(events[99].id == inputqueue.queue[99].id)

if __name__ == '__main__':
	unittest.main()
	# cProfile.run("unittest.main()")

