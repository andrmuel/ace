#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with Exception classes.
"""

class IncompleteEventInformationException(Exception):
	"""
	An exception indicating, that there was an attempt to create an event from
	incomplete information.
	"""
	def __init__(self, required):
		self.required = required
	def __str__(self):
		return "The following fields are required: "+str(self.required)

class UnknownEventFieldException(Exception):
	"""
	An exception indicating, that there was an attempt to create an event with
	an invalid field.
	"""
	def __init__(self, invalid):
		self.invalid = invalid
	
	def __str__(self):
		return "The following fields are invalid: "+str(self.invalid)

class UnknownEventStatusException(Exception):
	"""
	An exception indicating an unknown event status.
	"""
	def __init__(self, status):
		self.status = status
	def __str__(self):
		return "Event status is invalid: "+str(self.status)

class UnknownEventTypeException(Exception):
	"""
	An exception indicating an unknown event type.
	"""
	def __init__(self, type):
		self.type = type
	
	def __str__(self):
		return "Event type is invalid: "+str(self.type)

class RuleParserException(Exception):
	"""
	An exception during the parsing of the XML rules.
	"""
	def __init__(self, problem):
		self.description = problem

	def __str__(self):
		return "Exception during correlation rule parsing. "+self.description

class PluginNotFoundException(Exception):
	"""
	A condition or action plugin was not found.
	"""
	def __init__(self, plugintype, name):
		self.plugintype = plugintype
		self.name = name
	def __str__(self):
		return "The following plugin was not found: %s (type: %s)"\
		  % (self.name, self.plugintype)

class PluginException(Exception):
	"""
	An exception, when instantiating a plugin.
	"""
	def __init__(self, plugintype, name, problem):
		self.plugintype = plugintype
		self.name = name
		self.problem = problem
	def __str__(self):
		return "Exception in plugin '' (type: %s): %s"\
		  % (self.name, self.plugintype, self.problem)

class InputTranslatorNotFoundException(Exception):
	"""
	A requested input translator was not found.
	"""
	def __init__(self, name):
		self.name = name
	def __str__(self):
		return "Input translator '"+self.name+"' not found!"

class InputTranslatorException(Exception):
	"""
	An exception in an input translator.
	"""
	def __init__(self, num, name, problem):
		self.num = num
		self.name = name
		self.problem = problem

	def __str__(self):
		return "Exception in input translator "+str(self.num)+" ("+self.name+"): "+self.problem

class OutputTranslatorNotFoundException(Exception):
	"""
	A requested output translator was not found.
	"""
	def __init__(self, name):
		self.name = name
	def __str__(self):
		return "Output translator '"+self.name+"' not found!"

class OutputTranslatorException(Exception):
	"""
	An exception in an output translator.
	"""
	def __init__(self, num, name, problem):
		self.num = num
		self.name = name
		self.problem = problem
	def __str__(self):
		return "Exception in output translator "+str(self.num)+" ("+self.name+"): "+self.problem

class IOSourceNotFoundException(Exception):
	"""
	A requested source was not found.
	"""
	def __init__(self, name):
		self.name = name
	def __str__(self):
		return "IO source "+self.name+" not found!"

class IOSourceException(Exception):
	"""
	An exception in a source.
	"""
	def __init__(self, num, name, problem):
		self.num = num
		self.name = name
		self.problem = problem
	def __str__(self):
		return "Exception in IO source "+str(self.num)+" ("+self.name+"): "+self.problem

class IOSinkNotFoundException(Exception):
	"""
	A requested sink was not found.
	"""
	def __init__(self, name):
		self.name = name
	def __str__(self):
		return "IO sink "+self.name+" not found!"

class IOSinkException(Exception):
	"""
	An exception in a sink.
	"""
	def __init__(self, num, name, problem):
		self.num = num
		self.name = name
		self.problem = problem
	def __str__(self):
		return "Exception in IO sink "+str(self.num)+" ("+self.name+"): "+self.problem
