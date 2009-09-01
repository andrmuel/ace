#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Output with Python pickle module.
"""

try:
	import cPickle as pickle
except ImportError:
	import pickle

from ace.util import constants
from ace.translators.output.base import OutputTranslator

class EventPickler(OutputTranslator):
	"""
	Pickle based output translation.
	"""

	def translate(self, event):
		"""
		This is the main function, which translates an event into a pickle stream.
		"""
		# build a dict with the fields, which should be transmitted
		eventdata = dict([(key, event.__dict__[key])
		                   for key in constants.EVENT_FIELDS
		                   if event.__dict__.has_key(key)])
		# pickle and return it, separated by \xff (pickle uses ASCII representation, so this is ok)
		return pickle.dumps(eventdata)+'\xff'
