#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions

"""
File sink module.
"""

# stdlib
import sys
# own code
from ace.io.sinks.base import Sink

class FileSink(Sink):
	"""
	File sink.

	Configuration options:
	 - filename: filename of the output file (default: stdout)
	"""
	def __init__(self, num, config, logger, queue):
		Sink.__init__(self, num, config, logger, queue)
		if self.options.has_key('filename'):
			self.file = open(self.options['filename'], 'w')
		else:
			if self.config.daemon:
				self.raiseException("Can't use output to STDOUT and daemon mode at the same time.")
			else:
				self.file = sys.stdout

	def cleanup(self):
		"""
		Closes the file.
		"""
		if self.file != sys.stdout:
			self.file.close()

	def processEvent(self, event):
		"""
		Translates and outputs a single event.		
		"""
		self.file.write(self.translator.translate(event))
		if self.file == sys.stdout:
			self.file.flush()

	def writeOutput(self, output):
		"""
		Writes output to the file.
		"""
		self.file.write(output)
		if self.file == sys.stdout:
			self.file.flush()
