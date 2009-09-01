#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Classes for event handling.
"""

import hashlib
import random
import time
import operator

from ace.util import constants
from ace.util.exceptions import IncompleteEventInformationException
from ace.util.exceptions import UnknownEventFieldException
from ace.util.exceptions import UnknownEventTypeException
from ace.util.exceptions import UnknownEventStatusException


class Event:
	"""
	Represents a single event.
	"""
	def __init__(self, **kwargs):
		"""
		Creates a new event.
		
		Note that the following constraints must be satisfied by kwargs:
		  - all arguments must be valid event fields (as defined in constants)
		  - name and host are always required
		  - if an id is given (which means, that the event obviously already exists),
		    the arguments type, status, creation and description are required
		  - if the type is compressed, the argument count is required
		  - if type is given, it must be a legal event type (as defined in constants)
		  - if status is given, it must be a legal event status (as defined in constants)
		  - creation and arrival (if given) must be integers
		
		@param kwargs: keyword arguments
		@type  kwargs: dict
		@kwarg name: event name
		@type  name: string
		@kwarg host: host, where the event was created
		@type  host: string
		@kwarg description: an event description (default: empty string)
		@type  description: string
		@kwarg id: event ID (default: derive)
		@type  id: string
		@kwarg type: event type (default: raw)
		@type  type: string
		@kwarg status: event status (default: active)
		@type  status: string
		@kwarg creation: event creation time (seconds since 1970; default: current time)
		@type  creation: int
		@kwarg arrival: event arrival (seconds since 1970; default: current time)
		@type  arrival: int
		@kwarg local: whether to forward the event (default: True - event is not forwarded)
		@type  local: bool
		@kwarg count: number of represented events (default: empty)
		@type  count: int
		@kwarg attributes: additional attributes (default: empty)
		@type  attributes: dict
		@kwarg references: dict with lists with references (default: empty)
		@type  references: dict
		@kwarg history: list of dicts with event history (default: empty)
		@type  history: list
		
		@raise IncompleteEventInformationException: if the given parameters are not sufficient to create an event
		@raise UnknownEventFieldException: if a field other than the ones specified above is given
		@raise UnknownEventStatusException: if the event status is unknown
		@raise UnknownEventTypeException: if the event type is unknown
		@raise ValueError: if a string is found where an int is expected
		"""
		# check, whether the constraints mentioned above are fulfilled:
		if not set(kwargs.keys()).issubset(set(constants.EVENT_FIELDS)):
			raise UnknownEventFieldException(set(kwargs.keys()).difference(set(constants.EVENT_FIELDS)))
		always_required = set(['name', 'host'])
		if not always_required.issubset(kwargs.keys()):
			raise IncompleteEventInformationException(always_required.difference(set(kwargs.keys())))
		required_if_id = set(['description', 'type', 'status', 'creation'])
		if (kwargs.has_key('id') and not (required_if_id.issubset(kwargs.keys()))):
			raise IncompleteEventInformationException(required_if_id.difference(set(kwargs.keys())))
		if kwargs.has_key('type'):
			if not kwargs['type'] in constants.EVENT_TYPES:
				raise UnknownEventTypeException(kwargs['type'])
			if kwargs['type'] == 'compressed' and not kwargs.has_key('count'):
				raise IncompleteEventInformationException('count')
		if kwargs.has_key('status'):
			if not kwargs['status'] in constants.EVENT_STATUSES:
				raise UnknownEventStatusException(kwargs['status'])
		# create event
		currenttime = int(time.time())
		self.name = kwargs['name']
		self.host = kwargs['host']
		self.description = kwargs['description'] if kwargs.has_key('description') else "-"
		self.id = kwargs['id'] if kwargs.has_key('id') else\
		          hashlib.sha256("%s%.10f%.10f" % (self.host, time.time(), random.random())).hexdigest()
		self.type = kwargs['type'] if kwargs.has_key('type') else 'raw'
		self.status = kwargs['status'] if kwargs.has_key('status') else 'active'
		self.creation = kwargs['creation'] if kwargs.has_key('creation') else currenttime
		self.local = kwargs['local'] if kwargs.has_key('local') else False
		self.forwarded = False
		if kwargs.has_key('arrival'):
			self.arrival = int(kwargs['arrival'])
		else:
			self.arrival = currenttime
		if self.type == 'compressed':
			self.count = kwargs['count']
		if kwargs.has_key('attributes'):
			self.attributes = kwargs['attributes']
		if kwargs.has_key('references'):
			self.references = kwargs['references']
		if kwargs.has_key('history'):
			self.history = kwargs['history']
		# delay and cache time is arrival time until changed
		self.delaytime = self.arrival
		self.delaytime_rule = None
		self.cachetime = self.arrival
		self.cachetime_rule = None
		# references to contexts, which request delay or caching
		self.cache_contexts = set()
		self.delay_contexts = set()

	# def __cmp__(self, other):
		# """
		# Compare function. 
		#
		# @param other: other event
		# """
		# if self.id == other.id:
			# assert(self is other) # there must never be two different events with the same id!
			# return 0
		# elif self.name != other.name:
			# return cmp(self.name, other.name)
		# elif self.type != other.type:
			# return cmp(self.type, other.type)
		# elif self.host != other.host:
			# return cmp(self.host, other.host)
		# else:
			# return cmp(self.id, other.id)

	# def __hash__(self):
		# """
		# We use the id as event hash. 
		#
		# If we define __cmp__, we should also define __hash__, so set
		# operations, etc. are possible.
		# """
		# return int(self.id, 16)

	def __str__(self):
		# return self.name+' (type: '+self.type+', status: '+self.status\
				 # +', host: '+self.host+', id: '+self.id[0:8]+'...)'
		return self.name+' (type: '+self.type+', status: '+self.status\
				 +', host: '+self.host+', creation: '+str(self.creation)+'...)'

	def getContent(self):
		"""
		Returns the event content for the RPC server.
		"""
		return [{
		  'title': "Event information",
		  'type': "list",
		  'content': [
		    "Name: %s" % self.name,
		    "Description: %s" % self.description,
		    "Host: %s" % self.host,
		    "Type: %s" % self.type,
		    "Status: %s" % self.status,
		    "Count: %s" % self.getCount(),
		    "Creation: %s" % self.creation,
		    "Arrival: %s" % self.arrival,
		    "Local: %s" % self.local,
		    "Forwarded: %s" % self.forwarded,
		    "ID: %s" % self.id,
		    "Cache time: %s" % self.getCacheTime(),
		    "Cache time relative to arrival: %s" % (self.getCacheTime()-self.getArrivalTime()),
		    ["Rule responsible for cache time: "]+
		    (self.cachetime_rule.getLink() if self.cachetime_rule != None else ["n/a"]),
		    "Delay time: %s" % self.getDelayTime(),
		    "Delay time relative to arrival: %s" % (self.getDelayTime()-self.getArrivalTime()),
		    ["Rule responsible for delay time: "]+
		    (self.delaytime_rule.getLink() if self.delaytime_rule != None else ["n/a"]),
		  ]
		},{
		  'title': "Event attributes",
		  'type': "table",
		  'headers': ["Key","Value"],
		  'content': [[item[0],item[1]] for item in self.getAttributes().iteritems()]
		},{
		  'title': "Associated contexts prolonging delay time",
		  'type': "list",
		  'content':
		    [[{
		      'action': "show_context",
		      'args':{'group':context[0],
		      'name':context[1]},
		      'text': "%s / %s"%(context[0], context[1])
		    }] for context in self.getDelayContexts()]
		},{
		  'title': "Associated contexts prolonging cache time",
		  'type': "list",
		  'content':
		    [[{
		      'action': "show_context",
		      'args': {'group': context[0], 'name': context[1]},
		      'text': "%s::%s"%(context[0], context[1])
		    }] for context in self.getCacheContexts()]
		},{
		  'title': "Child references",
		  'type': "list",
		  'content': [[{'action':"show_event", 'args':{'event':reference}, 'text':"%s"%reference}]
		              for reference in self.getReferences('child')]
		},{
		  'title': "Cross references",
		  'type': "list",
		  'content': [[{'action':"show_event", 'args':{'event':reference}, 'text':"%s"%reference}]
		              for reference in self.getReferences('cross')]
		},{
		  'title': "Parent references",
		  'type': "list",
		  'content': [[{'action':"show_event", 'args':{'event':reference}, 'text':"%s"%reference}]
		              for reference in self.getReferences('parent')]
		},{
		  'title': "Event history",
		  'type': "table",
		  'headers': ["Timestamp", "Rulegroup", "Rule", "Host", "Fields", "Description"],
		  'content': [[entry['timestamp'], entry['rule']['groupname'], entry['rule']['rulename'],
		              entry['host'], ", ".join(entry['fields']) if entry.has_key('fields') else "",
		              entry['reason'] if entry.has_key('reason') else ""]
		              for entry in sorted(self.getHistory(), key=operator.itemgetter('timestamp'))]
		}]

	def getName(self):
		return self.name

	def getDescription(self):
		assert(type(self.description)==str)
		return self.description

	def getID(self):
		return self.id

	def getType(self):
		return self.type

	def setStatus(self, status):
		if not status in constants.EVENT_STATUSES:
			raise UnknownEventStatusException(status)
		self.status = status

	def getStatus(self):
		return self.status
		
	def isActive(self):
		"""
		Returns True if the event is still active.	
		"""
		return self.status == 'active'

	def getCount(self):
		if self.type != 'compressed':
			return 1
		else:
			return self.count

	def getHost(self):
		return self.host

	def getTimestamp(self, timeref="creation"):
		if timeref == "creation":
			return self.creation
		else:
			return self.arrival

	def getCreationTime(self):
		return self.creation

	def getArrivalTime(self):
		return self.arrival
	
	def hasAttribute(self, key):
		"""
		Returns True if the event as an attribute with the given key.
		"""
		if hasattr(self, 'attributes'):
			if self.attributes.has_key(key):
				return True
		return False

	def getAttribute(self, key):
		if hasattr(self, 'attributes'):
			if self.attributes.has_key(key):
				return self.attributes[key]
		return ""
	
	def getAttributes(self):
		if hasattr(self, 'attributes'):
			return self.attributes
		else:
			return dict()

	def setAttribute(self, key, value, op="set"):
		"""
		Set the given attribute (key) to the given value.
		
		If an existing attribute with the same key exists, it is overwritten.
		"""
		if not hasattr(self, 'attributes'):
			self.attributes = dict()
		if op == 'set':
			self.attributes[key] = str(value)
		else:
			if not self.attributes.has_key(key):
				self.attributes[key] = "0"
			if not self.attributes[key].isdigit():
				self.attributes[key] = "0"
			if op == 'inc':
				self.attributes[key] = str(int(self.attributes[key]) + int(value))
			elif op == 'dec':
				self.attributes[key] = str(int(self.attributes[key]) - int(value))
			else:
				assert(False) # should not happen - rule parser checks for correct op

	def checkAttribute(self, name, op, value, regexp=None):
		"""
		Checks whether the condition specified with the operator op and the
		given value is fulfilled by the attribute with the given name.
		"""
		if not hasattr(self, 'attributes'):
			return False
		if not self.attributes.has_key(name):
			return False
		if op in ["ge", "le", "eq"]:
			if op == "eq":
				return str(self.attributes[name]) == str(value)
			else:
				if not (value.isdigit() and self.attributes[name].isdigit()):
					return False
				if op == "ge":
					return int(self.attributes[name]) >= int(value)
				if op == "le":
					return int(self.attributes[name]) <= int(value)
		else:
			assert(op == "re")
			return bool(regexp.search(self.attributes[name]))

	def addReferences(self, reftype, references):
		"""
		Adds the given references to the event.
		"""
		assert(reftype in ['child', 'parent', 'cross'])
		if not hasattr(self, 'references'):
			self.references = dict()
		if not self.references.has_key(reftype):
			self.references[reftype] = list()
		for reference in references:
			if not reference.getID() in self.references[reftype]:
				self.references[reftype].append(reference.getID())

	def getReferences(self, reftype):
		assert(reftype=='child' or reftype=='parent' or reftype=='cross')
		if hasattr(self, 'references'):
			if self.references.has_key(reftype):
				return self.references[reftype]
		return []

	def getAllReferences(self):
		if hasattr(self, 'references'):
			return self.references
		else:
			return {}

	def addHistoryEntry(self, rule, hostname, tick, fields=None, reason=None):
		"""
		Adds an entry to the events history.
		"""
		if not hasattr(self, 'history'):
			self.history = list()
		entry = {'rule': rule, 'host': hostname, 'timestamp': tick}
		if fields != None:
			entry['fields'] = fields
		if reason != None:
			entry['reason'] = reason
		self.history.append(entry)

	def getHistory(self):
		if hasattr(self, 'history'):
			return self.history
		else:
			return []

	def getField(self, field):
		if field.startswith("attributes."):
			attribute = field.split('.')[1]
			return self.getAttribute(attribute)
		elif hasattr(self, field):
			return getattr(self, field)
		else:
			return ""

	def setLocal(self, local):
		self.local = local

	def getLocal(self):
		return self.local

	def wasForwarded(self):
		"""
		Returns True, if the event was already forwarded.
		"""
		return self.forwarded

	def getCacheTime(self):
		return self.cachetime

	def setCacheTime(self, when, rule=None):
		if when < self.delaytime:
			self.cachetime = self.delaytime
			self.cachetime_rule = self.delaytime_rule
		else:
			self.cachetime = when
			self.cachetime_rule = rule

	def getDelayTime(self):
		return self.delaytime

	def setDelayTime(self, when, rule=None):
		self.delaytime = when
		if self.cachetime < self.delaytime:
			self.cachetime = self.delaytime
			self.cachetime_rule = rule
		self.delaytime_rule = rule

	def addDelayContext(self, group, name):
		"""
		Adds a context to the events delay context list (the event is not
		forwarded as long as it has delay contexts).
		
		@param group: group of the context
		@param name: name of the context
		"""
		self.delay_contexts.add((group, name))

	def removeDelayContext(self, group, name):
		"""
		Removes the given context from the events delay context list.
		
		@param group: group of the context
		@param name: name of the context
		"""
		if (group, name) in self.delay_contexts:
			self.delay_contexts.remove((group, name))

	def hasDelayContexts(self):
		"""
		Checks, whether the event has at least one delay context.
		"""
		return len(self.delay_contexts) > 0

	def getDelayContexts(self):
		return self.delay_contexts

	def addCacheContext(self, group, name):
		"""
		Adds a cache context to the events cache context list (the event is
		kept in cache, as long as it has at least one cache context).
		
		@param group: group of the context
		@param name: name of the context
		"""
		self.cache_contexts.add((group, name))

	def removeCacheContext(self, group, name):
		"""
		Removes the given context from the events cache context list.
		
		@param group: group of the context
		@param name: name of the context
		"""
		if (group, name) in self.cache_contexts:
			self.cache_contexts.remove((group, name))

	def hasCacheContexts(self):
		"""
		Checks, whether the event has at least one cache context.
		"""
		return len(self.cache_contexts) > 0

	def getCacheContexts(self):
		return self.cache_contexts

class MetaEvent:
	"""
	This class can be used to represent a meta event for building the query
	table. Some properties of this event are undefined, others can be set to
	always True or always False.
	"""

	def __init__(self, name=None, eventtype=None, status=None, host=None):
		self.name = name
		self.type = eventtype
		self.status = status
		self.host = host

	def getName(self):
		return self.name

	def getType(self):
		return self.type

	def getStatus(self):
		return self.status

	def getHost(self):
		return self.host

	def getField(self, field):
		return ""

class EventGenerator:
	"""
	A class with methods to create events.
	"""

	def __init__(self, config=None):
		self.config = config

	def randomEvent(self, randomtime=False):
		"""
		Generate a random event (for testing purposes).
		"""
		if not randomtime:
			return Event(name = "CE:TESTEVENT:RANDOM",
			             description = "A random event for testing purposes.",
			             type = random.choice(constants.EVENT_TYPES),
			             status = random.choice(constants.EVENT_STATUSES),
			             host = 'host-'+str(random.randint(100, 999)),
			             count = random.randint(1,100))
		else:
			creation = random.randint(0, int(time.time()))
			arrival = random.randint(creation, int(time.time()))
			return Event(name = "CE:TESTEVENT:RANDOM",
			             description = "A random event for testing purposes.",
			             type = random.choice(constants.EVENT_TYPES),
			             status = random.choice(constants.EVENT_STATUSES),
			             host = 'host-'+str(random.randint(100, 999)),
			             count = random.randint(1,100),
			             creation = creation,
			             arrival = arrival)
						

	def randomEvents(self, n, randomtime=False):
		"""
		Generate a list with multiple random events (for testing purposes).
		
		@param n: number of generated events
		"""
		return [self.randomEvent(randomtime) for i in xrange(n)]

# main function
# note: this is for testing purposes only and will never be called during
#       normal operation
if __name__ == '__main__':
	g = EventGenerator()
	print g.randomEvent()
