#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions

"""
Null source module.
"""

from ace.io.sources.base import Source

class NullSource(Source):
	"""
	Null source.

	Never generates an event.
	"""

	def work(self):
		"""
		Lazy work function - does nothing.
		"""
		pass
