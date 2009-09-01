#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
TCP sink module.
"""

# stdlib
import time
import socket
import errno
# own code
from ace.io.sinks.base import Sink

class TCPSink(Sink):
	"""
	TCP sink.

	Configuration options:
	 - host: target hostname
	 - port: target port
	"""

	RETRY_DELAY_DEFAULT = 5
	CONNECT_RETRIES = 100

	def __init__(self, num, config, logger, queue):
		# parent
		Sink.__init__(self, num, config, logger, queue)
		# options
		if not self.options.has_key("host"):
			self.raiseException("No 'host' specified in options.")
		if not self.options.has_key("port"):
			self.raiseException("No 'port' specified in options.")
		if not self.options['port'].isdigit():
			self.raiseException("Option 'port': must be a number.")
		self.host = self.options['host']
		self.port = int(self.options['port'])
		self.connect_retries = self.CONNECT_RETRIES
		if self.options.has_key("connect_retries"):
			if self.options['connect_retries'].isdigit():
				self.retry_delay = int(self.options['connect_retries'])
		self.retry_delay = self.RETRY_DELAY_DEFAULT
		if self.options.has_key("retry_delay"):
			if self.options['retry_delay'].isdigit():
				self.retry_delay = int(self.options['retry_delay'])
		self.socket = socket.socket()

	def connect(self):
		"""
		Connects the socket.
		"""
		for i in range(self.connect_retries):
			if self.stop_processing:
				break
			try:
				self.logger.logDebug("Sink %d: trying to connect() socket (retry %d)."\
				                     % (self.num, i))
				self.socket.connect((self.host, self.port))
				return
			except socket.error as e:
				self.logger.logDebug("Sink "+str(self.num)+": socket.connect() error: "+str(e))
				if e.errno == errno.ECONNREFUSED:
					time.sleep(self.retry_delay)
				else:
					self.raiseException("Unhandled socket.connect() error: "+str(e))
		self.raiseException("socket.connect() unsuccessful; giving up after %d retries."\
		                    % self.connect_retries)

	def cleanup(self):
		"""
		Closes the socket.
		"""
		self.socket.close()
	
	def run(self):
		"""
		Connect and run.
		"""
		self.connect()
		Sink.run(self)

	def send(self, data):
		"""
		Tries to send the data (retries if there is an error).
		@param data: string with data
		"""
		while True:
			try:
				self.socket.sendall(data)
				return
			except socket.error as e:
				self.logger.logDebug("Sink "+str(self.num)+": socket.send() error: "+str(e))
				if e.errno == errno.EPIPE:
					self.logger.logDebug("Sink "+str(self.num)+": trying reconnect.")
					self.socket.close()
					self.socket = socket.socket()
					self.connect()
				else:
					self.raiseException("Unhandled socket.send() error.")

	def processEvent(self, event):
		"""
		Translates and sends a single event.
		"""
		self.send(self.translator.translate(event))

	def writeOutput(self, output):
		"""
		Sends data across the socket.
		
		@param output: data to send (string)
		"""
		self.send(output)
