#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Basis functions for rules.

This modules provides a set of basis functions for the rule components. These
functions can be combined to reperesent any function in the rule function space
(similar to how a linear combination of basis functions in mathematics can be
used to represent a function from the represented function space).
"""

import re
from ace.plugins import condition as condition_plugins
from ace.plugins import action as action_plugins

# the functions below are used at the time, when the rules are parsed, to build
# functions, which will be used to correlate events during run-time. the
# parameters of the generated functions are the following ones:
#  - rule       -> reference to calling rule
#  - trigger    -> reference to trigger event
#  - core
#  - rulemanager
#  - cache
#  - contexts
#  - selected_events (for actions/alt. actions only)
#  - query_events

def if_then_else(condition, actions, alternative_actions):
	"""
	Returns a function, which executes the actions, if the condition evaluates
	to True (at the time, the generated function is called), and otherwise the
	alternative actions.
	
	@param condition: a function, which takes any number of keyword arguments and returns a boolean value
	@param actions: a list with actions, which accept any number of keyword arguments
	@param alternative_actions: a list with actions, which accept any number of keyword arguments
	"""
	def if_then_else_generated(**kwargs):
		""" Dynamically generated function. """
		if condition(**kwargs):
			for action in actions:
				action(**kwargs)
		else:
			for action in alternative_actions:
				action(**kwargs)
	return if_then_else_generated

def and_(conditions):
	"""
	Returns a function, which returns true, if all of the given conditions
	evaluate to true (at the time, when the generated function is called).
	
	@param conditions: a list of conditions - functions, which accept and
	                   number of keyword arguments and return True or False
	"""
	# Explanation: if there are no conditions, a function, which returns true
	# for any arguments is returned. Otherwise, the condition list is reduced
	# with a function, which returns a function, which returns true, if both of
	# the two functions passed as arguments return true. Note that below, the
	# outer lambda statement generates a function, which will be used by reduce
	# and applied to the condition list, whereas the inner lambda defines the
	# function, which will be returned.
	if len(conditions) == 0:
		return true # this is the function defined below, not a boolean value!
	else:
		return reduce(lambda a, b: lambda **kwargs: a(**kwargs) and b(**kwargs), conditions)

def or_(conditions):
	"""
	Returns a function, which returns true, if any of the given conditions
	evaluates to true (at the time, when the generated function is called).
	
	@param conditions: a list of conditions - functions, which accept and
	                   number of keyword arguments and return True or False
	"""
	# just like and_, but with or :) - see above
	if len(conditions) == 0:
		return true # this is the function defined below, not a boolean value!
	else:
		return reduce(lambda a, b: lambda **kwargs: a(**kwargs) or b(**kwargs), conditions)
	

def not_(condition):
	"""
	Returns a function, which evaluates to true if the function passed as
	argument evaluates to false.
	
	@param condition: a function, which takes any number of keyword arguments and returns a boolean value
	"""
	return lambda **kwargs: not condition(**kwargs)

def context(group, namefunc, counter_val=None, op='ge'):
	"""
	Returns a function, which checks, whether the given context exists, and
	additionally, whether the counter condition is fullfilled, if specified.
	
	@param namefunc: name of the context
	@param group: rulegroup of the context
	@param counter_val: counter value
	@param op: comparison operator
	"""
	if counter_val != None:
		return lambda **kwargs:\
		  kwargs['contexts'].checkContextCounter(group, namefunc(**kwargs), counter_val, op)
	else:
		return lambda **kwargs: kwargs['contexts'].contextExists(group, namefunc(**kwargs))

def trigger_match(conditions):
	"""
	Returns a function, which checks, whether the specified conditions match
	the trigger.
	"""
	if len(conditions)==0:
		return true
	else:
		allconditions = intersection(conditions)
		# WARNING not all kwargs are passed 
		# -> might be a future problem source (i.e. if the DTD for trigger_match is changed)
		return lambda **kwargs:\
		  len(allconditions(query_events=[kwargs['trigger']], trigger=kwargs['trigger'])) > 0

def count(threshold, op, query):
	"""
	Returns a function, which counts the events selected by the given query.
	
	@param threshold: number of required events
	@type  threshold: int
	@param op: operator (eq/ge/le)
	@type  op: string
	"""
	if op == "eq":
		return lambda **kwargs: len(query(**kwargs)) == threshold
	elif op == "le":
		return lambda **kwargs: len(query(**kwargs)) <= threshold
	elif op == "ge":
		return lambda **kwargs: len(query(**kwargs)) >= threshold

def sequence(sort_by, match, queries):
	"""
	Returns a function, which checks, whether the events in the cache are
	selected by the queries in the specified order.
	"""
	assert(sort_by=="creation" or sort_by=="arrival")
	assert(match=="any" or match=="all")
	if len(queries) <= 1:
		return true
	if match == "any":
		def sequence_generated(**kwargs):
			""" Dynamically generated function. """
			events = [[e.getTimestamp(sort_by) for e in q(**kwargs)] for q in queries]
			current_min = -1
			for e in events:
				timestamp = [t for t in e if t > current_min]
				if len(timestamp) == 0:
					return False
				else:
					current_min = min(timestamp)
			return True
	else: # match all
		def sequence_generated(**kwargs):
			""" Dynamically generated function. """
			events = [[e.getTimestamp(sort_by) for e in q(**kwargs)] for q in queries]
			return all([max(events[i])<min(events[i+1]) for i in xrange(len(events)-1)])
	return sequence_generated

def pattern(alphabet, regexp):
	"""
	Returns a function, which checks, whether the events selected by the
	alphabet match the pattern specified in regexp.
	"""
	return lambda **kwargs: bool(regexp.search(alphabet(**kwargs)))

def alphabet(sort_by, symbols):
	"""
	Returns a function, which returns a string, which describes the event
	sequence according to the symbol specifications.
	
	@param sort_by: whether to use creation or arrival time
	@param symbols: symbol descriptions
	"""
	def alphabet_generated(**kwargs):
		""" Dynamically generated function. """
		alphabet = []
		matched_so_far = []
		for sym in symbols:
			matching = sym[1](**kwargs)
			matching = [e for e in matching if not e in matched_so_far] # no overlapping matches!
			matched_so_far.extend(matching)
			if sort_by == "creation":
				alphabet.extend([(sym[0], e.getCreationTime()) for e in matching])
			else:
				alphabet.extend([(sym[0], e.getArrivalTime()) for e in matching])
		alphabet.sort(key=lambda x: x[1])
		return reduce(lambda a, b: a + b, [symbol[0] for symbol in alphabet], "")
	return alphabet_generated


def symbol(letter, query):
	"""
	A single event symbol, represented by a letter and a corresponding event
	query.
	"""
	assert(len(letter)==1)
	return (letter, query)

def regexp(regexp):
	"""
	Returns the compiled regular expression for reg. Since all input data is
	known, there is no need to return a function.
	
	@param regexp: a string with a regular expression
	"""
	return re.compile(regexp)

def within(timeframe, timeref, match, event_queries):
	"""
	Returns a function, which checks, whether the events selected by the
	queries fit into the specified window.
	
	@param timeframe: time window
	@param timeref: time reference (creation or arrival time)
	@param match: whether it is sufficient that 'any' event from each query matches, or 'all' must match
	@param event_queries: query functions
	"""
	assert(type(timeframe)==int)
	assert(timeref=="creation" or timeref=="arrival")
	assert(match=="any" or match=="all")
	if len(event_queries)==0:
		return true
	if match == "all":
		def within_generated(**kwargs):
			""" Dynamically generated function. """
			events = [[e.getTimestamp(timeref) for e in q(**kwargs)] for q in event_queries]
			if min([len(e) for e in events])==0:
				return False
			events = reduce(lambda a, b: a + b, events, [])
			return max(events)-min(events) <= timeframe
	else:
		def within_generated(**kwargs):
			""" Dynamically generated function. """
			events = [[e.getTimestamp(timeref) for e in q(**kwargs)] for q in event_queries]
			return within_any(events, timeframe)
	return within_generated

def within_any(events, timeframe):
	"""
	Checks, whether there is a combination with at least one event from each group in
	the events list within a time window of the given length.
	
	@param events: list of lists with event timestamps
	@param timeframe: window length
	"""
	# Explanation (w = window length):
	#  1. At the start, we check, whether any group is empty, and the individual
	#     groups are sorted (this is simply to speed up things later)
	#  2. then we start with a window beginning with the first event (earlier
	#     makes no sense)
	#  3. Then, we look at the earliest event from each group and take the
	#     latest of them (time: tmax)
	#  4. If this event is within the window, we win (i.e. wo found a set
	#     within the window)
	#  5. Otherwise, we know, that we cannot start the window before tmax-w, as
	#     otherwise we would not have an event from the group with the event at
	#     tmax => new tmin=tmax-w
	#  6. We can discard all events from each group, which lie before tmin. If 
	#     any group has no events left, we lose; otherwise we continue at 2.
	#
	# Speed considerations: in each round, we either win (if at least one event
	# from each group is within the window), or we can remove at least one
	# event (as at least one event from one group is not within the window, the
	# window advances and we can certainly remove the event at the previous
	# start of the window). The worst case is thus O(n) rounds (n: total number
	# of events) with a round complexity O(m) (m: number of groups). Total
	# complexity is thus O(m*n) in the worst case; with a much better average
	# complexity (e.g. if the events are bursty, or one group has only few
	# events).
	#
	# Another possibility would be to recursively check (for each event
	# matching the first query) the nearest earlier and later event matching
	# subsequent queries. While this would be faster for few queries, it would
	# have an exponential complexity O(2^n), with n being the number of queries.
	for group in events:
		if len(group) == 0:
			return False
		group.sort()
	while True:
		tmin = min([group[0] for group in events])
		tmax = max([group[0] for group in events])
		if tmax <= tmin+timeframe:
			return True
		tmin = tmax-timeframe
		for group in events:
			while group[0] < tmin:
				group.pop(0)
				if len(group) == 0:
					return False

def condition_plugin(config, logger, name, parameters, queries):
	"""
	Returns a function, which executes the specified condition plugin, when it
	is called.
	"""
	plugin = condition_plugins.get_plugin(name)
	plugin_instance = plugin(config, logger, parameters, len(queries))
	def condition_plugin_generated(**kwargs):
		""" Dynamically generated function. """
		events = []
		for query in queries:
			events.append(query(**kwargs))
		# note: events should not be changed. for safety, we could pass a copy;
		# that would cost more resources however
		return plugin_instance.checkCondition(kwargs['trigger'], events)
	return condition_plugin_generated

# actions

def select_events(query, actions):
	"""
	Returns a function, which selects the events matched by the given query
	function, and executes the specified actions on the events.
	
	@param query: query function
	@param actions: list with action functions
	"""
	def select_events_generated(**kwargs):
		""" Dynamically generated function. """
		kwargs['selected_events'] = query(**kwargs)
		for action in actions:
			action(**kwargs)
	return select_events_generated

def drop(**kwargs): # a function, not a function generator!
	"""
	A function, which drops the specified events.
	Note that this is a function, not a function generator.
	
	@keyword selected_events: events to drop
	"""
	kwargs['cache'].dropEvents(kwargs['selected_events'])

def forward(**kwargs): # a function, not a function generator!
	"""
	A function, which forwards the specified events.
	Note that this is a function, not a function generator.
	
	@keyword selected_events: events to forward
	"""
	for event in kwargs['cache'].forwardEvents(kwargs['selected_events']):
		kwargs['core'].generateOutputEvent(event)

def compress(**kwargs): # a function, not a function generator!
	"""
	A function, which compresses the specified events.
	Note that this is a function, not a function generator.
	
	@keyword selected_events: events to compress
	"""
	for event in kwargs['cache'].compressEvents(kwargs['selected_events']):
		kwargs['rulemanager'].updateCacheAndDelayTime(event)
		kwargs['cache'].addEvent(event)

def aggregate(inject, eventfunc):
	"""
	Returns a function, which aggregates the specified events into a new event.
	
	@param inject: where to inject the new event: 'input' or 'output'
	@param eventfunc: function returning the new event
	"""
	assert(inject == "input" or inject == "output")
	def aggregate_generated(**kwargs):
		""" Dynamically generated function. """
		event = eventfunc(**kwargs)
		event['type'] = 'aggregated'
		if len(kwargs['selected_events']) > 0:
			event['references'] = {'child': list()}
			for e in kwargs['selected_events']:
				event['references']['child'].append(e.getID())
		newevent = kwargs['core'].createEvent(inject, event)
		if len(kwargs['selected_events']) > 0:
			for e in kwargs['selected_events']:
				e.addReferences('parent', [newevent])

	return aggregate_generated

def modify(status, local, rule, reason):
	"""
	Returns a function, which modifies the selected events.
	
	@param status: new value for status - 'active', 'inactive', or None for no modification
	@param local: new value for local field - True, False or None for no modification
	@param rule: responsible rule (group name, rule name)
	@param reason: reason for the modification (string)
	"""
	def modify_generated(**kwargs):
		""" Dynamically generated function. """
		events = kwargs['selected_events']
		core = kwargs['core']
		tick = core.ticker.getTick()
		hostname = core.config.hostname
		kwargs['cache'].removeStaleEventsFromList(events)
		for event in events:
			fields = []
			if status != None and status != event.getStatus():
				event.setStatus(status)
				fields.append('status')
			if local != None and local != event.getLocal():
				event.setLocal(local)
				fields.append('local')
			if len(fields) > 0:
				event.addHistoryEntry(rule, hostname, tick, fields, reason)
		core.addModifiedEvents(events)
	return modify_generated

def modify_attribute(name, value, op, rule, reason):
	"""
	Returns a function, which modifies an attribute of the selected events.
	
	@param name: name of the attribute
	@param value: new value
	@param op: operator
	@param rule: responsible rule (group name, rule name)
	@param reason: reason for the modification (string)
	"""
	def modify_attribute_generated(**kwargs):
		""" Dynamically generated function. """
		events = kwargs['selected_events']
		core = kwargs['core']
		tick = core.ticker.getTick()
		hostname = core.config.hostname
		kwargs['cache'].removeStaleEventsFromList(events)
		for event in events:
			event.setAttribute(name, value, op)
			event.addHistoryEntry(rule, hostname, tick, ['attributes'], reason)
		core.addModifiedEvents(events)
	return modify_attribute_generated

def suppress(rule, reason, query):
	"""
	Returns a function, which suppresses the selected events (sets status to
	"inactive" and adds parent references to the responsible events).
	
	@param rule: responsible rule (group name, rule name)
	@param reason: reason for the suppression (string)
	@param query: query function, which returns the responsible events
	"""
	def suppress_generated(**kwargs):
		""" Dynamically generated function. """
		events = kwargs['selected_events']
		core = kwargs['core']
		hostname = core.config.hostname
		tick = core.ticker.getTick()
		responsible_events = query(**kwargs)
		kwargs['cache'].removeStaleEventsFromList(events)
		active_events = [e for e in events if e.isActive()]
		for event in active_events:
			event.setStatus('inactive')
			event.addHistoryEntry(rule, hostname, tick, ['status'], reason)
			event.addReferences('parent', responsible_events)
		core.addModifiedEvents(active_events)
	return suppress_generated

def associate_with_context(group, namefunc):
	"""
	Returns a function, which associates the selected events with the given context.
	
	@param group: context group (string)
	@param namefunc: function returning the context name
	"""
	return lambda **kwargs: kwargs['contexts'].associateEventsWithContext(group,
	                                                                      namefunc(**kwargs),
	                                                                      kwargs['selected_events'])

def add_references(rule, reason, reftype, query):
	"""
	Returns a function, which adds references to the selected events, which
	point to the events returned by the query function.
	
	@param rule: responsible rule (group name, rule name)
	@param reason: description, why the references are added (string)
	@param reftype: type of the references - parent, child or cross
	@param query: query function to select the referenced events
	"""
	def add_references_generated(**kwargs):
		""" Dynamically generated function. """
		events = kwargs['selected_events']
		kwargs['cache'].removeStaleEventsFromList(events)
		references = query(**kwargs)
		for event in events:
			event.addReferences(reftype, references)
			event.addHistoryEntry(rule=rule,
			                      hostname=kwargs['core'].config.hostname,
			                      tick=kwargs['core'].ticker.getTick(),
			                      fields=['references'],
			                      reason=reason)
			kwargs['core'].addModifiedEvents(events)
	return add_references_generated

def create(inject, eventfunc):
	"""
	Returns a function, which creates a new event.
	
	@param inject: where to inject the new event - "input" or "output"
	@param eventfunc: function generating the event data
	"""
	def create_generated(**kwargs):
		""" Dynamically generated function. """
		event = eventfunc(**kwargs)
		event['type'] = 'synthetic'
		kwargs['core'].createEvent(inject, event)
	return create_generated

def create_context(group, namefunc, eventtuple, contextattribs):
	"""
	Returns a function, which generates a new context.
	
	@param group: group name
	@param namefunc: function returning the name of the new context
	@param eventtuple: event tuple for the event to be generated upon a context timeout (or None)
	@param contextattribs: context attributes (timeout, whether to recreate the context, etc.)
	"""
	def create_context_generated(**kwargs):
		""" Dynamically generated function. """
		name = namefunc(**kwargs)
		if eventtuple == None:
			event = None
		else:
			event = (eventtuple[0], eventtuple[1](**kwargs))
			event[1]['type'] = 'timeout'
		kwargs['contexts'].createContext(group, name, kwargs['rule'], event, contextattribs)
	return create_context_generated

def delete_context(group, namefunc):
	"""
	Returns a function, which deletes the specified context.
	
	@param group: group name
	@param namefunc: function returning the name of the new context
	"""
	return lambda **kwargs: kwargs['contexts'].deleteContext(group, namefunc(**kwargs))

def modify_context(group, namefunc, reset_timer, reset_associated_events, counter_op, counter_val):
	"""
	Returns a function, which modifies context attributes.
	
	@param group: group name
	@param namefunc: function returning the name of the new context
	@param reset_timer: whether to reset the contexts timer
	@param reset_associated_events: whether to clear the list of associated events
	@param counter_op: counter operation
	@param counter_val: value for the counter operation or None (don't change counter)
	"""
	def modify_context_generated(**kwargs):
		""" Dynamically generated function. """
		name = namefunc(**kwargs)
		kwargs['contexts'].modifyContext(group, name, reset_timer,
		                                 reset_associated_events,counter_op, counter_val)
	return modify_context_generated

def action_plugin(config, logger, name, parameters):
	"""
	Returns a function, which executes the given action plugin.
	
	@param config: reference to config instance
	@param logger: reference to logger instance
	@param name: name of the action plugin
	@param parameters: parameters for the action plugin
	"""
	plugin = action_plugins.get_plugin(name)
	plugin_instance = plugin(config, logger, parameters)
	return lambda **kwargs: plugin_instance.executeAction(kwargs['selected_events'])

def trigger(field):
	"""
	Returns a function, which returns the specified field from the trigger
	event.
	"""
	return lambda **kwargs: kwargs['trigger'].getField(field)

def event_query(query_operations, max_age, time_source):
	"""
	Returns a function, which returns the events selected by the given query.
	
	@param query_operations: list with zero or more query operations
	@param max_age: maximum age of a selected event
	@param time_source: creation or arrival ..
	"""
	query = intersection(query_operations)
	if max_age == None:
		def event_query_generated(**kwargs):
			""" Dynamically generated function. """
			kwargs['query_events'] = kwargs['cache'].getEvents()
			return query(**kwargs)
	else:
		def event_query_generated(**kwargs):
			""" Dynamically generated function. """
			kwargs['query_events'] = kwargs['cache'].getEvents()
			tick = kwargs['core'].ticker.getTick()
			return [event
			         for event in query(**kwargs)
			         if event.getTimestamp(time_source)+max_age >= tick]
	return event_query_generated

def intersection(queries):
	"""
	Returns a function, which returns all events, which match all of the passed
	queries.
	
	@param queries: list of event selection queries
	"""
	## more elegant, but slower:
	# return reduce(lambda a, b: lambda **kwargs: set(a(**kwargs)).intersection(b(**kwargs)),
	#               queries, lambda **kwargs: kwargs['query_events'])
	#
	# although less elegant, its more efficient to apply queries iteratively
	# (i.e. to apply the condition on the remaining events only each time):
	def intersection_generated(**kwargs):
		""" Dynamically generated function. """
		events = set(kwargs['query_events'])
		for query in queries:
			kwargs['query_events'] = list(events)
			events.intersection_update(query(**kwargs))
		return list(events)
	return intersection_generated

def union(queries):
	"""
	Returns a function, which returns all events, which match any of the passed
	queries.
	
	@param queries: list of event selection queries
	"""
	if len(queries)==0:
		return lambda **kwargs: kwargs['query_events']
	else:
		## more elegant, but slower:
		#return reduce(lambda a,b: lambda **kwargs: set(a(**kwargs)).union(b(**kwargs)), queries)
		# incremental version:
		def union_generated(**kwargs):
			""" Dynamically generated function. """
			events = kwargs['query_events']
			current = set(events)
			for query in queries:
				kwargs['query_events'] = list(current)
				current.difference_update(query(**kwargs))
			return list(set(events).difference(current))
		return union_generated

def complement(query):
	"""
	Returns a function, which returns the absolute complement of the events
	matched by the given query (i.e. the difference from the events in the
	cache minus the events matched by the query.
	
	@param query: event selection query
	"""
	return lambda **kwargs: list(set(kwargs['cache'].getEvents()).difference(query(**kwargs)))

def first_of(sort_by, query):
	"""
	Returns a function, which selects the oldest event in the set.
	
	@param sort_by: creation or arrival.
	@param query: returns the set, from which to select the first event
	"""
	def first_of_generated(**kwargs):
		""" Dynamically generated function. """
		events = query(**kwargs)
		if len(events) == 0:
			return events
		else:
			return [min(events, key=lambda e: e.getTimestamp(sort_by))]
	return first_of_generated

def last_of(sort_by, query):
	"""
	Returns a function, which selects the youngest event in the set.
	
	@param sort_by: creation or arrival.
	@param query: returns the set, from which to select the last event
	"""
	def last_of_generated(**kwargs):
		""" Dynamically generated function. """
		events = query(**kwargs)
		if len(events)==0:
			return events
		else:
			return [max(events, key=lambda e: e.getTimestamp(sort_by))]
	return last_of_generated

def unique_by(field, sort_by, keep, query):
	"""
	Returns a function, which selects one event for each unique value of the
	given field.
	
	@param field: event field
	@param sort_by: creation or arrival
	@param keep: whether to select the 'first' or 'last' event from the set for each unique value
	@param query: query, which returns the set to operate on
	"""
	def unique_by_generated(**kwargs):
		""" Dynamically generated function. """
		events = list(query(**kwargs))
		if keep == "first":
			events.sort(key=lambda e: e.getTimestamp(sort_by))
		else:
			events.sort(key=lambda e: e.getTimestamp(sort_by), reverse=True)
		out_events = []
		values = set()
		for event in events:
			fieldvalue = event.getField(field)
			if not fieldvalue in values:
				out_events.append(event)
				values.add(fieldvalue)
		return out_events
	return unique_by_generated

def is_trigger(**kwargs): # a function, not a generator!
	"""
	Returns only the trigger from the given events, if the trigger is in the
	list with events, and an empty list otherwise.
	
	@keyword query_events: events
	"""
	return [kwargs['trigger']] if kwargs['trigger'] in kwargs['query_events'] else []

def in_context(group, namefunc):
	"""
	Returns a function, which selects the events, which are associated with the
	given context.
	
	@param group: context group
	@param namefunc: function returning the context name
	"""
	def in_context_generated(**kwargs):
		""" Dynamically generated function. """
		context = (group, namefunc(**kwargs))
		if context == None:
			return []
		else:
			return [event for event in kwargs['query_events']
			              if context in event.getDelayContexts() or
			                 context in event.getCacheContexts()]
	return in_context_generated

def match_query(group, name):
	"""
	Returns a function, which returns the events, which match the given other query.
	
	@param group: group of the specified query
	@param name: name of the specified query
	"""
	return lambda **kwargs: kwargs['rulemanager'].getNamedQuery(group, name)(**kwargs)

def event_class(name):
	"""
	Returns a function, which selects the events with the given class.
	
	@param name: class name
	"""
	return lambda **kwargs: [event for event in kwargs['query_events']
	                          if name in kwargs['rulemanager'].getEventClasses(event)]

def event_name(name):
	"""
	Returns a function, which selects the events with the given name.
	
	@param name: event name
	"""
	return lambda **kwargs: [event for event in kwargs['query_events'] if event.name == name]

def event_type(eventtype):
	"""
	Returns a function, which selects the events with the given type.
	
	@param eventtype: event type
	"""
	return lambda **kwargs: [event for event in kwargs['query_events'] if event.type == eventtype]

def event_status(status):
	"""
	Returns a function, which selects the events with the given status.
	
	@param status: event status
	"""
	return lambda **kwargs: [event for event in kwargs['query_events'] if event.status == status]

def event_host(namefunc):
	"""
	Returns a function, which selects the events from the given host.
	"""
	return lambda **kwargs: [event for event in kwargs['query_events']
	                               if event.host == namefunc(**kwargs)]

def event_attribute(name, valuefunc, op, regexp=None):
	"""
	Returns a function, which selects the events with the given value for the
	specified attribute.
	"""
	if op == "re": # precompile the regular expression ..
		rex = re.compile(regexp) # Exception is cached in caller ..
		return lambda **kwargs: [event for event in kwargs['query_events']
		                               if event.checkAttribute(name, op, None, regexp=rex)]
	else:
		return lambda **kwargs: [event for event in kwargs['query_events']
		                               if event.checkAttribute(name, op, valuefunc(**kwargs))]

def event_min_age(age):
	"""
	Returns a function, which selects the events with the given minimum age
	(difference between creation and arrival time).
	"""
	return lambda **kwargs: [event for event in kwargs['query_events']
	                               if (event.arrival-event.creation) >= age]

def event(eventdata, descriptionfunc, attributefuncs):
	"""
	Returns a function, which returns event data for a new event.
	
	@param eventdata: given event data
	@param descriptionfunc: function returning a description for the new event
	@param attributefuncs: dict with attribute names (keys) and value functions (values)
	"""
	def event_generated(**kwargs):
		""" Dynamically generated function. """
		event = dict(eventdata)
		if descriptionfunc != None:
			event['description'] = descriptionfunc(**kwargs)
		if len(attributefuncs) > 0:
			event['attributes'] = {}
			for key in attributefuncs.keys():
				event['attributes'][key] = attributefuncs[key](**kwargs)
		event['host'] = kwargs['core'].config.hostname
		return event
	return event_generated

# other function generators (no direct correspondence with XML elements)

def mixed_content(initial_text, childfuncs):
	"""
	Generates a function, which returns a combination of the strings returned
	by the initial text and the passed functions.
	
	@param initial_text: initial string
	@param childfuncs: string generating functions (e.g. by extracting a field from the trigger)
	"""
	if initial_text == None:
		initial_text = ""
	return lambda **kwargs: reduce(lambda a, b: lambda **kwargs2: a(**kwargs2) + b(**kwargs2),
	                               childfuncs,
	                               lambda **kwargs3: initial_text)(**kwargs).strip()

# functions
#
# These functions have no, or only runtime arguments. Thus, we can reference
# the same function every time.

def true(*args, **kwargs):
	"""
	Takes any number and type of arguments and returns True.
	"""
	return True

def false(*args, **kwargs):
	"""
	Takes any number and type of arguments and returns False.
	"""
	return False
