#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
NOP translator module.
"""

from ace.translators.input.base import InputTranslator

class NOPTranslator(InputTranslator):
	"""
	A translator, that does nothing (and actually raises an exception, if it's
	translate function is called). To be used as a placeholder.
	"""
	pass
