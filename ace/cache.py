#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Event cache.
"""

import bisect

try:
	from blist import blist
except ImportError:
	blist = list # fallback to built-in list

from ace.event import Event
from ace.util import constants

class EventCache:
	"""
	Manages the events and determines, how long to store them.
	"""
	def __init__(self, config, logger, ticker):
		self.config = config
		self.logger = logger
		self.ticker = ticker
		self.events = set()        #: a set of all events in the cache
		self.delay_list = blist()  #: sorted list with event delay times -> tuple (delay time, event)
		self.cache_list = blist()  #: sorted list with event cache times -> tuple (cache time, event)
		self.dropped_events = 0    #: count of dropped events
		self.compressed_events = 0 #: number of events removed from cache because of compression
		self.new_compressed = 0    #: number of new compressed events
		self.nextcachewarning = 0  #: next time for warning about cache size exceeded

	def getContent(self):
		"""
		Returns the cache content for display in a UI.
		"""
		return [
		  {
		    'title': "General Cache Information",
		    'type': 'list',
		    'content': [
		      "Total number of events in the cache: %d" % len(self.events),
		      "Number of delayed events in the cache: %d" % self.getNumberOfDelayedEvents(),
		      "Number of cached events in the cache: %d" % self.getNumberOfCachedEvents(),
		      "Number of timestamps in the delay list: %d" % len(self.delay_list),
		      "Number of timestamps in the cache list: %d" % len(self.cache_list),
		      "Number of dropped events: %d" % self.dropped_events,
		      "Number of removed events due to compression: %d" % self.compressed_events,
		      "Number of new events due to compression: %d" % self.new_compressed,
		    ]
		  },{
		    'title': "Control",
		    'type': 'list',
		    'content': [[
		      {'action':"clear_cache",'args':{}, 'text':"Trigger cache cleanup"},
		      " (deletes *all* events in the cache!)"
		    ]]
		  },{
		    'title': "Sanity checks",
		    'type': 'list',
		    'content': [
		      "Events with unaccounted delay: %d" % len(self.getEventsWithUnaccountedDelay()),
		      "Events with unaccounted caching: %d" % len(self.getEventsWithUnaccountedCaching())
		    ]
		  },{
		    'title': "Events in the cache",
		    'type': 'table',
		    'headers': ["Name", "Type", "Status", "Forwarded", "Delay time", "Cache time", "Actions"],
		    'content': [[
		      e.getName(),
		      e.getType(),
		      e.getStatus(),
		      e.wasForwarded(),
		      e.getDelayTime(),
		      e.getCacheTime(),
		      [{'action':"show_event",'args':{'event':e.id},'text':"show"}]]
		    for e in sorted(self.events, key=lambda e:e.getArrivalTime())]
		  }]

	def getSize(self):
		return len(self.events)

	def getEventsWithUnaccountedDelay(self):
		"""
		Returns a list with events that shouldn't be delayed, but are.
		"""
		tick = self.ticker.getTick()
		return [e for e in self.events
		         if not (e.wasForwarded()
		                 or len(e.getDelayContexts()) > 0
		                 or e.getDelayTime() >= tick)]

	def getEventsWithUnaccountedCaching(self):
		"""
		Returns a list with events that shouldn't be in the cache, but are.
		"""
		tick = self.ticker.getTick()
		return [e for e in self.events
		         if not (len(e.getCacheContexts()) > 0
		                 or e.getCacheTime() >= tick
		                 or len(e.getDelayContexts()) > 0)]

	def getEventByID(self, eventid):
		"""
		Returns the event with the given id, or None if no event with this id
		is in the cache.
		
		@param eventid: Event ID.
		"""
		for event in self.events:
			if event.id == eventid:
				return event
		return None

	def updateCache(self):
		"""
		Update the cache -> check, which events are no longer needed and remove
		them (unless associated with a context).
		
		Note that this function is a generator, which possibly generates
		events, which need forwarding. It is the responsibility of the caller
		to do this.
		"""
		self.logger.logDebug("Updating cache - events in cache: ", len(self.events))
		tick = self.ticker.getTick()
		# check if the cache limit has been exceeded
		if len(self.events) > self.config.cache_max_size:
			if self.ticker.getTime() >= self.nextcachewarning:
				self.nextcachewarning = self.ticker.getTime()+3600
				self.logger.logWarn("Cache size limit (%d) exceeded." % self.config.cache_max_size)
				yield Event(name="CE:CACHE:LIMIT:EXCEEDED",
				            host=self.config.hostname,
				            type="internal",
				            local=False,
				            description="Too many events are in the cache.")
		# check whether events can be forwarded
		while len(self.delay_list)>0:
			# note: the timestamps in events_delay are considered just as
			# hints, that it might now be time to forward the event. things may
			# have changed since the timestamp was inserted, so we recheck
			# everything. this is easier than always looking for old timestamps
			# in the list, when the event is changed (even though the list is
			# sorted).
			if self.delay_list[0][0] >= tick:
				break
			event = self.delay_list.pop(0)[1]
			if event.getDelayTime() >= tick: # delay time has changed, so ignore this one
				continue
			if not event in self.events: # event is no longer in cache, -> must have been forwarded
				continue
			if not event.hasDelayContexts(): # contexts holding the event back?
				for e in self.forwardEvents([event]):
					yield e
		# check, whether events can be removed from cache
		while len(self.cache_list) > 0:
			# note: again, just hints (see above)
			if self.cache_list[0][0] >= tick:
				break
			event = self.cache_list.pop(0)[1]
			if event.getCacheTime()>=tick: # cache time has changed -> ignore this one
				continue
			if not event in self.events:
				continue
			if event.hasCacheContexts() or event.hasDelayContexts(): # context keeping evt in cache?
				continue
			if not event.wasForwarded():
				if not event.local:
					# we shouldn't get here - cache_time is always >= delay_time
					self.logger.logErr("EventCache: non-local event removed, "\
					                  +"that was never forwarded!")
				else:
					self.dropped_events += 1
			self.events.remove(event)
		self.logger.logDebug("Update done - events in cache: ", len(self.events))

	def clearCache(self):
		"""
		Removes all events from the cache, be recreating the events set, the
		delay list and the cache list.
		"""
		self.logger.logNotice("EventCache: clearing event cache.")
		self.events = set()
		self.delay_list = blist()
		self.cache_list = blist()

	def hasDelayedEvents(self):
		"""
		Checks, whether there are any entries in the delay list, which
		reference events, that actually still need to be forwarded.
		"""
		for e in self.delay_list:
			if e[1] in self.events:
				if not (e[1].wasForwarded() == True or e[1].getLocal() == True):
					return True
		return False

	def getNumberOfDelayedEvents(self):
		"""
		Returns the number of delayed events in the cache.
		"""
		return len([e for e in self.events if not e.wasForwarded()])

	def getNumberOfCachedEvents(self):
		"""
		Returns the number of cached events in the cache.
		"""
		return len([e for e in self.events if e.wasForwarded()])

	def insertDelayTimestamp(self, timestamp, event):
		"""
		Insert event's delay timestamp into the delay list in the right
		position.
		"""
		bisect.insort_right(self.delay_list, (timestamp, event))

	def insertCacheTimestamp(self, timestamp, event):
		"""
		Insert event's cache timestamp into the cache list in the correct
		position.
		"""
		bisect.insort_right(self.cache_list, (timestamp, event))

	def insertEventCacheAndDelayTime(self, event):
		"""
		Insert event's delay and cache timestamp into the corresponding lists.
		"""
		self.insertCacheTimestamp(event.getCacheTime(), event)
		self.insertDelayTimestamp(event.getDelayTime(), event)

	def removeEventCacheAndDelayTime(self, event):
		"""
		Remove cache and delay timestamps.
		"""
		# cache time
		cachetime = event.getCacheTime()
		cachepos = bisect.bisect_left(self.cache_list, (cachetime, event))
		if self.cache_list[cachepos][1] == event:
			self.logger.logDebug("Removing event from cache_list: ", event)
			self.cache_list.pop(cachepos)
		else:
			self.logger.logDebug("Event not in cache_list: ", event)
		# delay time
		delaytime = event.getDelayTime()
		delaypos = bisect.bisect_left(self.delay_list, (delaytime, event))
		if self.delay_list[delaypos][1] == event:
			self.logger.logDebug("Removing event from delay list: ", event)
			self.delay_list.pop(delaypos)
		else:
			self.logger.logDebug("Not in delay_list: ", event)

	def getEvents(self):
		return self.events

	def addEvent(self, event):
		"""
		Adds the given event to the cache.
		
		@param event: event to add
		"""
		if not event in self.events:
			self.logger.logDebug("Adding to cache: ", event)
			self.events.add(event)
			self.insertEventCacheAndDelayTime(event)
		else:
			self.logger.logErr("Duplicate event: %s" % event)

	def addEvents(self, events):
		"""
		Adds the given events to the cache.
		
		@param events: list with events to add
		"""
		for event in events:
			self.addEvent(event)

	def dropEvent(self, event):
		"""
		Drop the specified event immediately and unconditionally.
		
		@param event: event to drop
		"""
		if event in self.events:
			self.dropped_events += 1
			self.events.remove(event)
			self.removeEventCacheAndDelayTime(event)

	def dropEvents(self, events):
		"""
		Drop specified events immediately, and even if they are associated with
		a context.
		
		@param events: list with events to drop
		"""
		for event in events:
			self.dropEvent(event)

	def forwardEvents(self, events):
		"""
		Forwards the specified events, if the event has not been forwarded
		previously.
		
		Note that this function is a generator. It is the responsibility of the
		caller (i.e. the core) to actually generate output events.
				
		@param events: list of events to forward
		"""
		for event in events:
			assert(event in self.events)
			if event.forwarded == False and event.local == False:
				self.logger.logDebug("Forwarding event: ", event)
				event.forwarded = True
				yield event

	def forwardAll(self):
		"""
		Forwards all remaining events.
		"""
		delayed = [event for event in self.events
		            if event.forwarded == False and event.local == False]
		delayed.sort(key = lambda e: e.getCreationTime())
		for event in self.forwardEvents(delayed):
			yield event

	def removeStaleEventsFromList(self, events):
		"""
		Removes all events that are not (or no longer) in the cache from the
		given event list.
		
		Note: this function modifies it's argument, and does not generate a new list.
		
		@param events: list with events
		"""
		for event in events:
			if not event in self.events:
				self.logger.logDebug("Not in cache: ", event)
				events.remove(event)

	def compressEvents(self, events):
		"""
		Compresses multiple events with the same name into one event with a
		count.
		
		This is a generator functions, which yields new events.
		"""
		self.removeStaleEventsFromList(events)
		raw_or_compressed = [e for e in events
		                       if (e.getType() in ['raw', 'compressed'])
		                          and not e.wasForwarded()
		                          and not e.hasCacheContexts()  # Note: maybe still allow compression?
		                          and not e.hasDelayContexts()] # Note: maybe still allow compression?
		names = set([e.getName() for e in raw_or_compressed])
		for name in names:
			evts = [e for e in raw_or_compressed if e.getName() == name]
			if len(evts)<=1:
				continue
			# build the new event:
			newevent = {'name': name, 'type': 'compressed'}
			newevent['count'] = sum([e.getCount() for e in evts])
			# description
			if len(set([e.getDescription() for e in evts])) == 1: # same description everywhere
				newevent['description'] = evts[0].getDescription()
			else:
				newevent['description'] = ""
			# host
			if len(set([e.getHost() for e in evts])) == 1: # same host everywhere
				newevent['host'] = evts[0].getHost()
			else:
				newevent['host'] = self.config.hostname
			# status
			if len(set([e.getStatus() for e in evts])) == 1:
				newevent['status'] = evts[0].getStatus()
			else:
				newevent['status'] = 'active'
			# creation timestamp
			newevent['creation'] = min([e.getCreationTime() for e in evts])
			# attributes
			newevent['attributes'] = dict()
			keys = []
			for e in evts:
				keys.extend(e.getAttributes().keys())
			keys = list(set(keys)) # make unique
			for key in keys:
				values = [e.getAttribute(key) for e in evts if e.hasAttribute(key)]
				if len(set(values)) == 1:
					newevent['attributes'][key] = values[0]
				else:
					newevent['attributes'][key] = "[multiple values]"
			# references
			newevent['references'] = {}
			for eventtype in constants.EVENT_REFERENCE_TYPES:
				newreferences = set()
				for e in evts:
					newreferences.update(e.getReferences(eventtype))
					if len(newreferences) > 0:
						newevent['references'][eventtype] = list(newreferences)
			# local field
			if len(set([e.getLocal() for e in evts])) == 1:
				newevent['local'] = evts[0].getLocal()
			else:
				newevent['local'] = False
			# arrival time
			newevent['arrival'] = min([e.getArrivalTime() for e in evts])
			# add new event
			self.new_compressed += 1
			new = Event(**newevent)
			yield new
			# remove old ones
			self.compressed_events += len(evts)
			for e in evts:
				self.events.remove(e)
				self.removeEventCacheAndDelayTime(e)
