#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides a function to select and load the correct source class at run time.
"""

from ace.util.exceptions import IOSourceNotFoundException

from ace.io.sources.file import FileSource
from ace.io.sources.tcp import TCPSource
from ace.io.sources.ticker import TickerSource
from ace.io.sources.null import NullSource

SOURCES = {
	'file': FileSource,
	'tcp': TCPSource,
	'ticker': TickerSource,
	'null': NullSource
}

def get_source(source):
	"""
	Returns the class of the source with the given name.
	
	@param source: source name
	"""
	if not SOURCES.has_key(source):
		raise IOSourceNotFoundException(source)
	else:
		return SOURCES[source]
