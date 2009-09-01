#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
File source module.
"""

# stdlib
import sys
import select
# own code
from ace.io.sources.base import Source

class FileSource(Source):
	"""
	File source.

	Configuration options:
	 - filename: filename of inputfile (default: stdin)
	"""
	def __init__(self, num, config, logger, queue):
		Source.__init__(self, num, config, logger, queue)
		if self.options.has_key('filename'):
			try:
				self.file = open(self.options['filename'], 'r')
			except IOError, e:
				self.raiseException(str(e))
		else:
			if self.config.simulation:
				self.raiseException("Can't use input from STDIN in simulation mode.")
			elif self.config.python_console or self.config.ipython_console:
				self.raiseException("Can't use input from STDIN and interactive console at the same time.")
			elif self.config.daemon:
				self.raiseException("Can't use input from STDIN and daemon mode at the same time.")
			else:
				self.file = sys.stdin

	def cleanup(self):
		"""
		Closes the file.
		"""
		if self.file != sys.stdin:
			self.file.close()

	def work(self):
		"""
		Reads lines, while the file doesn't block and has more input.
		"""
		# select returns the file descriptors, on which read() will not block;
		# the file may still be at EOF, and read() may return an empty string
		while len(select.select([self.file], [], [], 0)[0]) > 0:
			content = self.file.readline()
			if len(content)>0:
				for event in self.translator.translate(content):
					self.queue.put(event)
			else:
				break
