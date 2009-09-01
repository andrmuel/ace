#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
TCP source module.
"""

# stdlib
import SocketServer
# own code
from ace.io.sources.base import Source

# class TCPHandler(SocketServer.StreamRequestHandler):
class TCPHandler(SocketServer.BaseRequestHandler):
	"""
	RequestHandler for the TCP source.

	This class is instantiated once for each connection.
	"""

	BUFSIZE = 4096

	def setup(self):
		"""
		Get ready for handling the connection.	
		"""
		self.num = self.server.parent.num
		self.config = self.server.parent.config
		self.logger = self.server.parent.logger
		self.queue = self.server.parent.queue
		self.translator = self.server.parent.Translator(self.num, self.config, self.logger)

	def handle(self):
		"""
		Handle a single connection.
		"""
		# note: possible race-condition: this daemonic handler thread could
		# receive data after the source has already shut down, and the input
		# queue has been joined. while this should not result in a deadlock or
		# an exception, the data would be lost
		data = self.request.recv(self.BUFSIZE)
		while data:
			for event in self.translator.translate(data):
				self.queue.put(event)
			data = self.request.recv(self.BUFSIZE)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	"""
	Makes the TCP server threaded (otherwise, the server is synchronous).
	"""
	pass	

class TCPSource(Source):
	"""
	TCP source.

	Configuration options:
	 - port: listen port
	 - address: bind address (default: empty -> INADDR_ANY)
	"""
	def __init__(self, num, config, logger, queue):
		Source.__init__(self, num, config, logger, queue)
		if self.options.has_key("address"):
			self.address = self.options['address']
		else:
			self.address = ""
		if not self.options.has_key("port"):
			self.raiseException("No 'port' specified in options.")
		if not self.options['port'].isdigit():
			self.raiseException("Option 'port': must be a number.")
		self.port = int(self.options['port'])
		# create server
		if self.config.simulation: # synchronous
			self.server = SocketServer.TCPServer((self.address, self.port), TCPHandler)
		else: # asynchronous, threaded
			self.server = ThreadedTCPServer((self.address, self.port), TCPHandler)
			self.server.daemon_threads = True # child threads shouldn't prevent exit
		self.server.parent = self

	def finish(self):
		"""
		Stop the source and shutdown the server.
		"""
		Source.finish(self)
		if not self.config.simulation:
			self.server.shutdown()

	def work(self):
		"""
		Simply starts the server (normal mode) or handles one single connection
		(simulation mode).
		"""
		if self.config.simulation:
			self.server.handle_request() # just take input from one connection
		else:
			self.server.serve_forever()
