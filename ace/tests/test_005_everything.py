#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest
import os
import sys

from ace.master import Master
from ace.util import configuration

class TestEverything(unittest.TestCase):
	"""
	Unittest, which test individual elements of a complete CE.
	"""
	
	def setUp(self):
		self.basedir = os.path.dirname(os.path.abspath(sys.modules[__name__].__file__))+"/"
		self.config = configuration.Config()
		self.config.loglevel = 0
		self.config.verbosity = 0
		self.config.realtime = False

	# def testDefaultPolicyForward(self):
		# self.config.rulefile = self.basedir+"rules/005_empty.xml"
		# master = Master(self.config)
		# master.run()

	def tearDown(self):
		pass

if __name__ == '__main__':
	unittest.main()

