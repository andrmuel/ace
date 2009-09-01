#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Basis functions for queries.

Note: these functions are relevant for event cache and delay time determination
only. The functions for event selection can be found in the rulecomponents
module.
"""

import re
from ace.util.constants import DEFINED, UNDEFINED

# arguments for the generated functions
#
# - event -> event under scrutiny
# - rulemanager -> provides event classes

def event_query(query_operations, max_age, time_source):
	"""
	Returns a function for Boolean evaluation of an event query.
	"""
	return intersection(query_operations)

def intersection(queries):
	"""
	For cache/delay time determination, this is a ternary logic 'and'.
	
	0 and 0 -> 0
	0 and 1 -> 0
	1 and 0 -> 0
	1 and 1 -> 1
	u and 0 -> 0
	u and 1 -> u
	0 and u -> 0
	1 and u -> u
	u and u -> u
	0 and d -> 0
	1 and d -> d
	u and d -> u
	d and 0 -> 0
	d and 1 -> d
	d and u -> u
	d and d -> d
	"""
	def intersection_generated_bool(**kwargs):
		""" Dynamically generated function. """
		result = True
		for query in queries:
			q_result = query(**kwargs)
			if q_result == False:
				return False # one False is sufficient to make 'and' False
			elif q_result == DEFINED and result != UNDEFINED:
				result = DEFINED
			elif q_result == UNDEFINED:
				result = UNDEFINED
		return result
	return intersection_generated_bool

def union(queries):
	"""
	Ternary logic 'or'.
	
	0 or 0 -> 0
	0 or 1 -> 1
	1 or 0 -> 1
	1 or 1 -> 1
	u or 0 -> u
	u or 1 -> 1
	0 or u -> u
	1 or u -> 1
	u or u -> u
	0 or d -> d
	1 or d -> 1
	u or d -> u
	d or 0 -> d
	d or 1 -> 1
	d or u -> u
	d or d -> d
	"""
	if len(queries) == 0:
		return true
	else:
		def union_generated_bool(**kwargs):
			""" Dynamically generated function. """
			result = False
			for query in queries:
				q_result = query(**kwargs)
				if q_result == True:
					return True # one True is sufficient to make 'or' True
				elif q_result == DEFINED and result != UNDEFINED:
					result = DEFINED
				elif q_result == UNDEFINED:
					result = UNDEFINED
			return result
		return union_generated_bool

def complement(query):
	"""
	Ternary logic 'not'.
	
	not 0 -> 1
	not 1 -> 0
	not u -> u
	not d -> d
	"""
	def complement_generated_bool(**kwargs):
		""" Dynamically generated function. """
		q_result = query(**kwargs)
		if type(q_result) == bool:
			return not q_result
		else:
			return q_result
	return complement_generated_bool

def first_of(sort_by, query):
	"""
	Oldest in set -> we need to keep all events that match the contained query,
	because each event could possibly be the oldest one.
	"""
	return lambda **kwargs: query(**kwargs)

def last_of(sort_by, query):
	"""
	Youngest in set -> we need to keep all events that match the contained
	query, because each event could possibly be the youngest one.
	"""
	return lambda **kwargs: query(**kwargs)

def unique_by(field, sort_by, keep, query):
	"""
	Unique by a given attribute - could be any of the contained, so return
	whatever the contained query returns.
	"""
	return lambda **kwargs: query(**kwargs)

def is_trigger(*args, **kwargs):
	"""
	We never have to keep an event in the cache because of 'is_trigger',
	because it actually is always false for any cached or delayed event.
	"""
	return False

def in_context(group, namefunc):
	"""
	We don't cache or delay events due to this element, because the contexts
	already do that themselves.
	"""
	return false # Note: might create confusion in some cases

def match_query(group, name):
	"""
	Event matches another query?
	"""
	return false # Note: match_query should cache or delay the event

def event_class(name):
	"""
	Checks, whether an event belongs to the given class.
	
	Uses the predet_wrapper.
	"""
	return predet_wrapper(
	  "event_class",
	  lambda **kwargs: name in kwargs['rulemanager'].getEventClasses(kwargs['event'])
	)

def event_name(name):
	"""
	Simply checks the name of the event.

	Uses the predet_wrapper.
	"""
	return predet_wrapper(
	  "event_name",
	  lambda **kwargs: kwargs['event'].getName() == name
	)

def event_type(eventtype):
	"""
	Checks whether the event type matches the given one.

	Uses the predet_wrapper.
	"""
	return predet_wrapper(
	  "event_type",
	  lambda **kwargs: kwargs['event'].getType() == eventtype
	)

def event_status(status):
	"""
	Checks whether the event status matches the given one.

	Uses the predet_wrapper.
	"""
	return predet_wrapper(
	  "event_status",
	  lambda **kwargs: kwargs['event'].getStatus() == status
	)

def event_host(namefunc):
	"""
	If possible, checks whether the event host matches the given one (this is
	only possible, if the name contains no <trigger> element).

	Uses the predet_wrapper.
	"""
	if namefunc() == UNDEFINED:
		return predet_wrapper(
		  "event_host",
		  undefined
		)
	else:
		return predet_wrapper(
		  "event_host",
		  lambda **kwargs: kwargs['event'].getHost() == namefunc(**kwargs)
		)

def event_attribute(name, valuefunc, op, regexp=None):
	"""
	If possible, checks the event attribute (this is only possible, if the
	specified value contains no <trigger> element).

	Uses the predet_wrapper.
	"""
	if op == "re": # precompile the regular expression ..
		rex = re.compile(regexp) # Exception is cached in caller ..
		return predet_wrapper(
		  "event_attribute",
		  lambda **kwargs: kwargs['event'].checkAttribute(name, op, rex)
		)
	elif valuefunc() == UNDEFINED:
		return predet_wrapper(
		  "event_attribute",
		  undefined
		)
	else:
		return predet_wrapper(
		  "event_attribute",
		  lambda **kwargs: kwargs['event'].checkAttribute(name, op, valuefunc(**kwargs))
		)

def event_min_age(age):
	"""
	Minimum age (difference between creation and arrival time).

	Uses the predet_wrapper.
	"""
	return predet_wrapper(
		  "event_min_age",
		  lambda **kwargs: kwargs['event'].getArrivalTime()-kwargs['event'].getCreationTime() >= age
		)

def trigger(field):
	"""
	Returns a placeholder function, which should never be called.
	"""
	def trigger_generated_bool(**kwargs):
		""" Placeholder, which should never be called. """
		assert(False) # should never be called (wouldn't make sense either)
	return trigger_generated_bool

def mixed_content(initial_text, childfuncs):
	"""
	Returns a function returning the text, if possible; the undefined function
	otherwise (if trigger information would be needed for the text).
	"""
	if len(childfuncs) > 0:
		return undefined
	else:
		return lambda **kwargs: initial_text

# helpers

def predet_wrapper(field, func):
	"""
	Wraps the passed function, so that the field can be preset to a given
	value.
	
	@param field: name of the field (string)
	@param func: function to be wrapped
	"""
	def predet_wrapper_generated_bool(**kwargs):
		""" Dynamically generated function. """
		if kwargs.has_key('predetermined_fields'):
			if kwargs['predetermined_fields'].has_key(field):
				return kwargs['predetermined_fields'][field]
			elif kwargs['predetermined_fields'].has_key('default'):
				return kwargs['predetermined_fields']['default']
		return func(**kwargs)
	return predet_wrapper_generated_bool

def defined(**kwargs):
	"""
	This function returns DEFINED independently of the arguments.
	"""
	return DEFINED

def undefined(**kwargs):
	"""
	This function returns UNDEFINED independently of the arguments.
	"""
	return UNDEFINED

def true(**kwargs):
	"""
	This function returns True independently of the arguments.
	"""
	return True

def false(**kwargs):
	"""
	This function returns False independently of the arguments.
	"""
	return False
