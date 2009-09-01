#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides a function for output translator loading.
"""

from ace.util.exceptions import OutputTranslatorNotFoundException

# translators
from ace.translators.output.linebased import LineBased
from ace.translators.output.xml_translator import XMLTranslator
from ace.translators.output.pickle_translator import EventPickler
from ace.translators.output.nop import NOPTranslator

TRANSLATORS = {
	'linebased': LineBased,
	'xml': XMLTranslator,
	'pickle': EventPickler,
	'nop': NOPTranslator
}

def get_translator(translator):
	"""
	Returns corresponding class for the specified translator.	
	"""
	if not TRANSLATORS.has_key(translator):
		raise OutputTranslatorNotFoundException(translator)
	else:
		return TRANSLATORS[translator]
