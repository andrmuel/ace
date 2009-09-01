#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Simple line-based output. 
"""

from ace.translators.output.base import OutputTranslator

class LineBased(OutputTranslator):
	"""
	Line based output translation.
	"""

	def translate(self, event):
		"""
		This is the main function, which translates an event into an output line.
		"""
		return str(event)+"\n"
