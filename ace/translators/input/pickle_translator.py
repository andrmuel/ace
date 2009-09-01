#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Classes for translation of line based input.
"""

# stdlib
try:
	import cPickle as pickle
except ImportError:
	import pickle
# own code
from ace.translators.input.base import InputTranslator
from ace.event import Event

class EventUnpickler(InputTranslator):
	"""
	Input translation of pickle'd events.
	"""

	def __init__(self, num, config, logger):
		InputTranslator.__init__(self, num, config, logger)
		self.leftover = ""

	def translate(self, inputdata):
		"""
		This is the main function, which processes the input.
		"""
		inputdata = self.leftover + inputdata
		picklestreams = inputdata.split('\xff')
		self.leftover = picklestreams[-1]
		for event in picklestreams[:-1]:
			yield Event(**pickle.loads(event))
