#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Classes for context management and representation.
"""

import Queue
import bisect

class ContextManager:
	"""
	Manages contexts.

	The data structure, which contains the contexts is a nested dictionary
	(with the group as key on the first level, and the context name as key on
	the second level). Furthermore, there is a list with timestamps of possible
	context timeouts, which is always kept in a sorted state.
	"""
	def __init__(self, config, logger, ticker, cache):
		self.config = config
		self.logger = logger
		self.ticker = ticker
		self.cache = cache
		self.contexts = {}
		self.contexts_to_delete = Queue.Queue() # Queue with locking -> avoid synchronisation problems
		self.context_timeouts = []

	def getContent(self):
		"""
		Returns the context manager content for display in a UI.
		"""
		return [
		  {
		    'title': "General Context Manager Information",
		    'type': 'list',
		    'content': [
		      "Total number of contexts: %d" % self.getNumberOfContexts(),
		      "Number of groups with contexts: %d" % len(self.contexts),
		    ]
		  },{
		    'title': "Sanity checks",
		    'type': 'list',
		    'content': [
		      "Number of stale contexts: %d" % len(self.getStaleContexts()),
		    ]
		  },{
		    'title': "Groups with contexts",
		    'type': 'table',
		    'headers': ["Group name", "Number of contexts"],
		    'content': [[groupname, len(self.contexts[groupname])] for groupname in sorted(self.contexts)]
		  }]+[{
		    'title': "Contexts in group '%s'" % groupname,
		    'type': "table",
		    'headers': ["Context name", "Timeout", "Counter", "Associated events", "Actions"],
		    'content': [[
		      context.name,
		      context.timeout,
		      context.counter,
		      len(context.associated_events),
		      [{
		          'action': "show_context",
		          'text': "show",
		          'args': {'group': groupname, 'name': context.name}
		        }, " / ", {
		          'action': "delete_context",
		          'text': "delete",
		          'args': {'group': groupname, 'name': context.name}
		      }]
		      ] for context in sorted(self.contexts[groupname].values())]
		  } for groupname in self.contexts]

	def getNumberOfContexts(self):
		return sum([len(group) for group in self.contexts.values()])

	def getStaleContexts(self):
		tick = self.ticker.getTick()
		stale = []
		for group in self.contexts.values():
			for context in group.values():
				if context.getRelativeTimeout() != 0 and context.getAbsoluteTimeout() < tick:
					stale.append(context)
		return stale

	def mayGenerateTimeoutEvents(self):
		"""
		Checks, whether there is at least one context in the context manager,
		which might yet produce a context timeout event.
		"""
		for group in self.contexts.values():
			for context in group.values():
				if context.eventtuple != None and context.timeout != 0:
					return True
		return False

	def hasGroup(self, group):
		"""
		Checks, whether there is a rule group with the given name, which has a
		context.
		
		@param group: group name
		"""
		return self.contexts.has_key(group)

	def getGroup(self, group):
		if self.contexts.has_key(group):
			return self.contexts[group]
		else:
			return None

	def hasContext(self, group, name):
		"""
		Checks, whether the group with the given name has a context with the
		given name.
		
		@param group: group name
		@param name: context name
		"""
		if self.hasGroup(group):
			if self.contexts[group].has_key(name):
				return True
		return False

	def getContext(self, group, name):
		if self.hasContext(group, name):
			return self.contexts[group][name]
		else:
			return None

	def createContext(self, group, name, rule, event, contextattribs):
		"""
		Creates a new context.
		
		@param group: rule group creating the context
		@param name: name of the context
		@param rule: reference to the rule, which created the context
		@param event: dict with timeout event description or None
		@param contextattribs: context attributes
		"""
		if not self.contexts.has_key(group):
			self.contexts[group] = {}
		if self.contexts[group].has_key(name): # context already exists
			self.logger.logDebug("Context %s::%s already exists." % (group, name))
		else:
			context = Context(group, name, rule, self.ticker.getTick(), event, **contextattribs)
			self.contexts[group][name] = context
			self.insertContextTimeout(context)

	def insertContextTimeout(self, context):
		"""
		Inserts the timeout of the given context into the context_timeouts list.
		@param context: Context instance
		"""
		bisect.insort_right(self.context_timeouts, (context.getAbsoluteTimeout(), context))

	def triggerDeleteContext(self, group, name):
		"""
		Asks the context manager to delete the specified context during the
		next update.
		"""
		self.contexts_to_delete.put((group, name))

	def deleteContext(self, group, name):
		"""
		Immediately deletes the specified context and forwards the associated
		events (if any).
		"""
		if self.contexts.has_key(group):
			if self.contexts[group].has_key(name):
				context = self.contexts[group].pop(name)
				self.forwardAssociatedEvents(context)
				if len(self.contexts[group]) == 0:
					self.contexts.pop(group)

	def deleteGroup(self, group):
		"""
		Deletes all contexts of the given group, and then the group itself.
		
		@param group: group name
		"""
		while self.contexts.has_key(group):
			self.deleteContext(group, self.contexts[group].keys()[0])

	def deleteGroups(self, groups):
		"""
		Deletes the given context groups, including all contexts.
		
		@param groups: list with groups
		"""
		for group in groups:
			self.deleteGroup(group)

	def modifyContext(self, group, name, reset_timer, reset_associated_events,
	                  counter_op, counter_value):
		"""
		Wrapper for the context's modifyContext function (which shouldn't be
		called directly).
		"""
		if self.contextExists(group, name):
			context = self.contexts[group][name]
			if reset_associated_events:
				self.forwardAssociatedEvents(context)
			context.modifyContext(self.ticker.getTick(),
			                      reset_timer,
			                      reset_associated_events,
			                      counter_op,
			                      counter_value)
			if reset_timer:
				self.insertContextTimeout(context)
		else:
			self.logger.logWarn("ContextManager: modifyContext: context "\
			                   +"'%s :: %s' does not exist." % (group, name))

	def contextExists(self, group, name):
		"""
		Checks, whether the given context exists.
		
		@param group: context group
		@param name: context name
		"""
		if self.contexts.has_key(group):
			if self.contexts[group].has_key(name):
				return True
		return False

	def checkContextCounter(self, group, name, value, op):
		"""
		Checks the condition specified by op on the context specified by its
		name and group.
		
		@param group: context group
		@param name: context name
		@param value: counter value
		@type  value: int
		@param op: operator (ge, le or eq)
		"""
		if not self.contextExists(group, name):
			return False
		else:
			return self.contexts[group][name].checkCounter(value, op)

	def associateEventsWithContext(self, group, name, events):
		"""
		'Cross-associates' the given events with the specified context.
		"""
		if self.contexts.has_key(group):
			if self.contexts[group].has_key(name):
				self.contexts[group][name].associateWithEvents(events)
				if self.contexts[group][name].delay_associated:
					for event in events:
						event.addDelayContext(group, name)
				else:
					for event in events:
						event.addCacheContext(group, name)
			else: # only a problem in the rules
				self.logger.logDebug("Context '%s::%s' not known." % (group, name))
		else:
			self.logger.logDebug("Context group '%'s not known." % group)

	def forwardAssociatedEvents(self, context):
		"""
		Forwards the events associated with the given context, if necessary.
		For convenience, we just insert new timestamps in the cache and let the
		cache do the work.
		"""
		for event in context.getAssociatedEvents():
			if context.delay_associated:
				event.removeDelayContext(context.group, context.name)
				if not event.hasDelayContexts():
					self.cache.insertDelayTimestamp(self.ticker.getTick()-1, event)
				if not event.hasCacheContexts():
					self.cache.insertCacheTimestamp(self.ticker.getTick()-1, event)
			else:
				event.removeCacheContext(context.group, context.name)
				if not event.hasCacheContexts():
					self.cache.insertCacheTimestamp(self.ticker.getTick()-1, event)

	def updateContexts(self):
		"""
		Context update -> delete contexts, whose deletion was requested by the
		user, and check for context timeouts.	
		
		Note that this function is a generator, which possible yields new
		events -> it is the responsibility of the caller (core), to inject
		events into the queues.
		"""
		if self.logger.log_debug:
			self.logger.logDebug("Updating contexts (number of contexts: %d)."\
			                     % self.getNumberOfContexts())
		# contexts, for which a delete was requested by the user
		while not self.contexts_to_delete.empty():
			(group, name) = self.contexts_to_delete.get()
			self.deleteContext(group, name)
			self.contexts_to_delete.task_done()
		# check timeouts, create events if necessary
		tick = self.ticker.getTick()
		while len(self.context_timeouts) > 0:
			# note: the timestamps are just hints; the context may have changed
			if self.context_timeouts[0][0] >= tick:
				break
			context = self.context_timeouts.pop(0)[1]
			(group, name) = context.group, context.name
			if context.getAbsoluteTimeout() >= tick: # timeout time has changed, so ignore this one
				continue
			if not group in self.contexts.keys(): # context was deleted -> ignore
				continue
			if not name in self.contexts[group].keys(): # context was deleted -> ignore
				continue
			# if we got so far, we have a timeout
			# generate a context timeout event if necessary
			if context.eventtuple != None:
				context.eventtuple[1]['references'] = {
				  'child': [e.getID() for e in context.getAssociatedEvents()]
				}
				context.eventtuple[1]['attributes'] = {
				  'context_counter': str(context.counter)
				}
				yield context.eventtuple
			# delete or reset the context
			if context.repeat:
				# some events may need forwarding
				self.forwardAssociatedEvents(context)
				# reset it
				context.resetContext(tick)
				self.insertContextTimeout(context)
			else:
				self.deleteContext(group, name)
		if self.logger.log_debug:
			self.logger.logDebug("Update done (number of contexts: %d)."\
			                     % self.getNumberOfContexts())

	def cleanupContexts(self, groups):
		"""
		Remove any contexts of groups, which no longer exist.	
	
		@param groups: a list of groups, which exist (i.e. all groups not in
		the list are cleaned)
		"""
		for group in set(self.contexts.keys()).difference(set(groups)):
			while self.contexts.has_key(group):
				self.deleteContext(group, self.contexts[group].keys()[0])

class Context:
	"""
	Represents a single context.
	"""
	def __init__(self, group, name, rule, currenttick, eventtuple, timeout, counter=0,
	             repeat=False, delay_associated=False):
		self.group = group
		self.name = name
		self.rule = rule
		self.creation = currenttick
		self.eventtuple = eventtuple
		self.timeout = timeout
		self.counter = counter
		self.counter_init = counter
		self.repeat = repeat
		self.delay_associated = delay_associated
		self.associated_events = set()

	def __str__(self):
		return "%s::%s" % (self.name, self.group)

	def getContent(self):
		return [{
		  'title': "General information",
		  'type': "list",
		  'content': [
		    "Name: %s" % self.name,
		    "Group: %s" % self.group,
		    "Relative timeout: %d" % self.timeout,
		    "Context creation or timer reset: %d" % self.creation,
		    "Absolute timeout: %d" % (self.creation+self.timeout),
		    "Counter: %d" % self.counter,
		    "Repeat: "+str(self.repeat),
		    "Delay associated events: "+str(self.delay_associated),
		    "Number of associated events: %d" % len(self.associated_events),
		    ["Rule responsible for creation: "]+self.rule.getLink(),
		  ]
		},{
		  'title': "Associated events",
		  'type': "list",
		  'content': [
		    [{
		      'action': "show_event",
		      'text': str(event),
		      'args': {'event': event.getID()}
		    }] for event in self.associated_events]
		}]

	def getRelativeTimeout(self):
		return self.timeout

	def getAbsoluteTimeout(self):
		return self.creation+self.timeout

	def resetContext(self, tick):
		"""
		Resets timer, counter and associated events.
		"""
		self.creation = tick
		self.counter = self.counter_init
		self.associated_events = set()

	def checkCounter(self, value, op):
		"""
		Check, whether the counter has at least/most/exactly (according to op) the given value.
		"""
		assert(value == None or type(value)==int)
		assert(op=="eq" or op=="le" or op=="ge")
		if op == 'eq':
			return self.counter == value
		if op == 'ge':
			return self.counter >= value
		if op == 'le':
			return self.counter <= value

	def setCounter(self, value):
		self.counter = value
	
	def addCounter(self, value):
		"""
		Add the given value to the counter.
		
		@param value: positive or negative integer value
		"""
		if not hasattr(self, 'counter'):
			self.counter = 0
		self.counter += value

	def getAssociatedEvents(self):
		return self.associated_events
	
	def associateWithEvents(self, events):
		"""
		Add the given events to the set of associated events.
		"""
		self.associated_events.update(set(events))

	def modifyContext(self, tick, reset_timer, reset_associated_events, counter_op, counter_value):
		"""
		Modifies the context's properties.
		
		Note: should not be called directly - use modifyContext from the
		ContextManager instead.
		"""
		if reset_timer:
			self.creation = tick
		if reset_associated_events:
			self.associated_events = []
		if counter_value != None:
			if counter_op == 'set':
				self.counter = counter_value
			elif counter_op == 'inc':
				self.counter += counter_value
			else:
				self.counter -= counter_value
