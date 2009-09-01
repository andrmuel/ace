#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Runs all tests in the tests/ directory.
"""

import unittest
import os
import sys

# slight hack to import all test classes:
cur_dir = os.path.dirname(os.path.abspath(sys.modules[__name__].__file__))+"/"
modules = [file for file in os.listdir(cur_dir+"tests")
                if file.startswith("test_") and file.endswith(".py")]
for module in modules:
	exec 'from ace.tests.'+module[:-3]+' import *'

# runs all test classes:
if __name__ == '__main__':
	unittest.main()

