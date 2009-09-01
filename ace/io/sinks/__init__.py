#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides a function to select and load the correct sink class at run time.
"""

from ace.util.exceptions import IOSinkNotFoundException

from ace.io.sinks.file import FileSink
from ace.io.sinks.tcp import TCPSink
from ace.io.sinks.rpc import RPCSink
from ace.io.sinks.null import NullSink

SINKS = {
	'file': FileSink,
	'tcp': TCPSink,
	'rpc': RPCSink,
	'null': NullSink
}

def get_sink(sink):
	"""
	Returns the class of the sink with the given name.
	
	@param sink: name of the sink
	"""
	if not SINKS.has_key(sink):
		raise IOSinkNotFoundException(sink)
	else:
		return SINKS[sink]
