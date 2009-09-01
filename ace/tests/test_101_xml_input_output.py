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

from ace.util import configuration, logging, constants
from ace.io.sources import FileSource
from ace.io.sinks import FileSink
from ace.translators.input import xml_translator as xmlinputtranslator
from ace.translators.output import xml_translator as xmloutputtranslator
from ace import event

class TestXMLIO(unittest.TestCase):
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
		self.config.simulation = True
		self.config.fast_exit = False
		self.config.events_dtd = self.basedir+"events.dtd"
		self.logger = logging.Logger(self.config)

	def testXMLRead(self):
		self.config.input = [{'source':"file:filename="+self.basedir+"test_101_events.xml", 'translator':"xml"}]
		source = FileSource(0, self.config, self.logger, self.queue)
		source.work()
		source.finish()
		
		self.assert_(self.queue.qsize()==2)
		event1 = self.queue.get()
		event2 = self.queue.get()
		self.assert_(event1.getName()=="NIC:ETHERNET:LINKUP")
		self.assert_(event1.getDescription()=="The ethernet network internet controller is up.")
		self.assert_(event1.getID()=="e9294e806d02fd8ebd90e345434c16a3")
		self.assert_(event1.getType()=="raw")
		self.assert_(event1.getStatus()=="active")
		self.assert_(event1.getHost()=="host-a-0")
		self.assert_(event1.getTimestamp()==1243039102)
		self.assert_(len(event1.getAttributes())==1)
		self.assert_(event1.getAttribute("interface")=="1")
		self.assert_(event2.getName()=="MAIL:FRESHCLAM:ERROR")
		self.assert_(event2.getHistory()==[{"host":"host-b-0", "rule":{"groupname": "freshclam", "rulename": "detect-single-events"}, "timestamp": 1244014940, "fields": ["status"], "reason": "Single errors can be ignored."}])

	def testXMLWrite(self):
		"""
		Just to check that all is running and there are no validation errors.
		"""
		self.config.input = [{'source':"file:filename="+self.basedir+"test_101_events.xml", 'translator':"xml"}]
		source = FileSource(0, self.config, self.logger, self.queue)
		source.work()
		source.finish()
		self.config.output = [{'sink':"file:filename=/dev/null", 'translator':"xml"}]
		sink = FileSink(0, self.config, self.logger, self.queue)
		sink.start()
		self.queue.join()
		sink.finish()
		sink.join()

	def testRandomEvents(self):
		g = event.EventGenerator()
		out_trans = xmloutputtranslator.XMLTranslator(0, self.config, self.logger)
		in_trans = xmlinputtranslator.XMLTranslator(0, self.config, self.logger)
		events = g.randomEvents(100)
		xmlstring = constants.EVENT_TAG_EVENTS_START
		for e in events:
			xmlstring += out_trans.translate(e)
		xmlstring += constants.EVENT_TAG_EVENTS_END
		events2 = []
		for e in in_trans.translate(xmlstring):
			events2.append(e)
		self.assert_(len(events)==len(events2))
		for i in range(len(events)):
			events2[i].arrival = events[i].arrival
			events2[i].cachetime = events[i].cachetime
			events2[i].delaytime = events[i].delaytime
			self.assert_(events[i].__dict__==events2[i].__dict__)

		

if __name__ == '__main__':
	unittest.main()
	# cProfile.run("unittest.main()")

