#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
NOP translator - does nothing.
"""

from ace.translators.output.base import OutputTranslator

class NOPTranslator(OutputTranslator):
	"""
	A translator, that never generates any output (and actually raises an
	exception, if it's translate function is called). To be used e.g. together
	with the RPC sink, as a placeholder.
	"""
	pass
