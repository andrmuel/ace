#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
A module with a simple letter input translator.

This translator is useful only for testing.
"""

from ace.translators.input.base import InputTranslator
from ace.event import Event

class Letter(InputTranslator):
	"""
	Letter based input translator, which creates a new event from each
	alphabetic letter in the input stream. Most likely only useful for testing.
	"""

	def translate(self, inputdata):
		"""
		This is the main function, which processes the input.
		"""
		for letter in inputdata:
			if letter.isalpha():
				yield Event(name=letter, host=self.config.hostname)
