#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
RPC sink module.
"""


# stdlib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import SocketServer
# own code
from ace.util import constants
from ace.io.sinks.base import Sink

class ThreadedRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer):
	"""
	Subclass of the SimpleXMLRPCServer with ThreadingMixIn.
	"""
	pass

class RPCSink(Sink):
	"""
	RPC sink. This sink forwards events as Event instances and doesn't need a
	translator.

	Configuration options:
	 - address: determines, on which address the socket listens
	 - port: port of the RPC server
	"""
	def __init__(self, num, config, logger, queue):
		Sink.__init__(self, num, config, logger, queue)
		if not self.options.has_key("address"):
			self.raiseException("No 'address' specified in options.")
		if not self.options.has_key("port"):
			self.raiseException("No 'port' specified in options.")
		if not self.options['port'].isdigit():
			self.raiseException("Option 'port': must be a number.")
		self.address = self.options['address']
		self.port = int(self.options['port'])
		self.server = SimpleXMLRPCServer((self.address, self.port), logRequests=False, allow_none=True)
		self.server.register_function(self.getEvents)

	def finish(self):
		"""
		Stop the sink and shut the server down.
		"""
		Sink.finish(self)
		self.server.shutdown()

	def run(self):
		"""
		The main thread function.
		"""
		self.server.serve_forever()
	
	def getEvents(self):
		events = []
		while self.queue.qsize()>0:
			event = self.queue.get()
			events.append(dict([(k, event.__dict__[k])
			                    for k in constants.EVENT_FIELDS
			                    if event.__dict__.has_key(k)]))
			self.queue.task_done()
		return events
