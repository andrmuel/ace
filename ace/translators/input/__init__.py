#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides a function for input translator loading.
"""

from ace.util.exceptions import InputTranslatorNotFoundException
# translators:
from ace.translators.input.linebased import LineBased
from ace.translators.input.letter import Letter
from ace.translators.input.xml_translator import XMLTranslator
from ace.translators.input.pickle_translator import EventUnpickler
from ace.translators.input.csvdump import CSVDumpTranslator
from ace.translators.input.nop import NOPTranslator

TRANSLATORS = {
	'linebased': LineBased,
	'letter': Letter,
	'xml': XMLTranslator,
	'pickle': EventUnpickler,
	'csvdump': CSVDumpTranslator,
	'nop': NOPTranslator
}

def get_translator(translator):
	"""
	Returns the class for the input translator with the given name.
	
	@param translator: translator name
	"""
	if not TRANSLATORS.has_key(translator):
		raise InputTranslatorNotFoundException(translator)
	else:
		return TRANSLATORS[translator]
