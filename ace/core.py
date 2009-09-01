#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Correlation engine core.

This module implements the core class of the correlation engine.
"""

import threading
import copy
from ace import rulebase
from ace import cache
from ace import contexts
from ace import event

class EventHandler(threading.Thread):
	"""
	Main class, which reacts on incoming events.
	"""

	def __init__(self, config, logger, ticker, inputqueue, outputqueues):
		# log
		logger.logInfo("EventHandler (core): init.")
		# parent
		threading.Thread.__init__(self)
		# parameters
		self.config = config
		self.logger = logger
		self.ticker = ticker
		self.inputqueue = inputqueue
		self.outputqueues = outputqueues
		# internal variables
		self.reload_rules = False
		self.clear_cache = False
		self.generated_input_events = []
		self.modified_events = set()
		self.stop_processing = False
		self.input_processed = 0
		self.output_generated = 0
		self.new_events = 0
		# rule manager
		self.rulemanager = rulebase.RuleManager(self.config, self.logger)
		# event cache
		self.cache = cache.EventCache(self.config, self.logger, self.ticker)
		# context manager
		self.contextmanager = contexts.ContextManager(self.config, self.logger, self.ticker, self.cache)

	def getContent(self):
		"""
		Returns the core content for display in a UI.
		"""
		return [
		  {
		    'title': "General Event Handler Information",
		    'type': 'list',
		    'content': [
		      "Average event processing rate: %3.2f events per minute" % (self.processingRate()*60),
		      "Processed input events: %d" % self.input_processed,
		      "Internally generated new events: %d" % self.new_events,
		      "Events waiting in internal queue: %d" % len(self.generated_input_events),
		      "Generated output events: %d" % self.output_generated,
		      "Modified events requiring timestamp update: %d" % len(self.modified_events),
		    ]
		  },{
		    'title': "Control",
		    'type': 'list',
		    'content': [[{
		      'action': "reload_rules", 'args': {}, 'text' : "Trigger reload of correlation rules"
		    }]]
		  },{
		    'title': "Sanity checks",
		    'type': 'list',
		    'content': [
		      "Event balance: %d" % self.getEventBalance()
		    ]
		  }]

	def getEventBalance(self):
		"""
		The balance of events should be zero:
		
		input + new - waiting - delayed - dropped + (compress new - dropped) =
		output
		"""
		return (self.input_processed
		       +self.new_events
		       -len(self.generated_input_events)
		       -self.cache.getNumberOfDelayedEvents()
		       -self.cache.dropped_events
		       +self.cache.new_compressed
		       -self.cache.compressed_events
		       -self.output_generated)

	def processingRate(self):
		"""
		Returns the average processing rate in events per second.
		"""
		return float(self.input_processed)/(self.ticker.getTime()-self.ticker.starttime)

	def reloadRules(self):
		"""
		Sets a variable to indicate, that the correlation rules should be
		reloaded, as soon as there is time.
		"""
		self.logger.logInfo("Reload of correlation rules requested.")
		self.reload_rules = True

	def triggerClearCache(self):
		"""
		Sets a variable to indicate, that the cache should be cleared.
		"""
		self.logger.logInfo("Cache clearing requested.")
		self.clear_cache = True

	def finish(self):
		"""
		Called from Master. It sets a variable to indicate, that the
		correlation engine should stop processing input.
		"""
		self.stop_processing = True
		self.logger.logDebug("Finishing.")

	def createEvent(self, inject, eventdata):
		"""
		Creates a new event and injects it into the internal array with
		generated input events or the output queues.
		
		@param inject: where to inject the event - 'input' or 'output'
		@param eventdata: a dict with event data
		"""
		self.new_events += 1
		eventdata['creation'] = self.ticker.getTick()
		eventdata['arrival'] = self.ticker.getTick()
		newevent = event.Event(**eventdata)
		if inject == "input":
			self.generated_input_events.append(newevent)
		else:
			self.generateOutputEvent(newevent)
		return newevent

	def generateOutputEvent(self, event):
		"""
		Put the event into each output queue. Note that a copy is put in the
		queues, so that later changes will not affect the output event.
		
		@param event: the event to put in the queue
		"""
		# we make a copy, but each output queue get's the same copy
		self.output_generated += 1
		eventcopy = copy.deepcopy(event)
		for queue in self.outputqueues:
			queue.put(eventcopy)

	def addModifiedEvents(self, events):
		"""
		Adds the events to to core's list of modified events, so their cache
		and delay time will be reevaluated at the end of the current tick.	
		
		@param events: list of events
		"""
		self.modified_events.update(events)

	def run(self):
		"""
		The main thread run function - simply calls work() until it is stopped.
		"""
		# core main loop
		while not self.stop_processing:
			self.work()
		# forward remaining events
		while len(self.generated_input_events) > 0 and not self.config.fast_exit:
			self.work()
		if not self.config.fast_exit:
			for event in self.cache.forwardAll():
				self.generateOutputEvent(event)
		# end of main processing loop
		self.logger.logInfo("EventHandler: exiting - %d input events " % self.input_processed\
		                   +"processed and %d output events generated." % self.output_generated)
		self.logger.logInfo("EventHandler: internal balance at exit: %d." % self.getEventBalance())

	def work(self):
		"""
		This is the main work function. It does the work of one step and
		processes the events according to the following plan:
		
		 - if a rule reload has been requested: ask the rule manager to do it
		 - update contexts (check whether there are timeouts)
		   - if necessary generate events for context timeouts
		 - clean up the event cache
		   - remove old events
		     - if there is no query yet requiring the event
		     - if there is no associated context
		   - forward events that need forwarding
		 - process all input events for the current timestep and produce output events
		   - if simulation: wait for all input for current timestep first
		 - advance Ticker
		   - if necessary, the ticker will wait until this second is over,
		     before advancing to the next tick
		"""
		# rule reload?
		if self.reload_rules:
			changedgroups = self.rulemanager.reloadRules()
			self.contextmanager.deleteGroups(changedgroups)
			self.contextmanager.cleanupContexts(self.rulemanager.rulegroups.keys())
			self.reload_rules = False
		# update contexts
		for event in self.contextmanager.updateContexts():
			self.createEvent(event[0], event[1])
		# update event cache
		for event in self.cache.updateCache():
			self.generateOutputEvent(event)
		# process input events of the current step
		while len(self.generated_input_events) > 0 or self.inputqueue.qsize() > 0:
			if len(self.generated_input_events) > 0:
				event = self.generated_input_events.pop(0)
				event_from_queue = False
				self.logger.logDebug("Processing internal event: ", event)
			else:
				if self.inputqueue.queue[0].getArrivalTime() > self.ticker.getTick():
					# the event is from a future time step -> advance the ticker
					break
				else:
					event = self.inputqueue.get()
					event_from_queue = True
					self.logger.logDebug("Processing event from input queue: ", event)
			self.rulemanager.updateCacheAndDelayTime(event)
			self.cache.addEvent(event)
			rules = self.rulemanager.getRelevantRules(event)
			for rule in rules:
				if (not event in self.cache.getEvents()) or (not event.isActive()):
					# event has been dropped, compressed or made inactive (by a previous rule)
					break
				self.logger.logDebug("Starting execution of rule: ", rule)
				rule.execute(trigger=event, core=self, rulemanager=self.rulemanager,
				             cache=self.cache, contexts=self.contextmanager)
			# signal the queue, that the Event has been processed
			if event_from_queue:
				self.inputqueue.task_done()
				# count processed events for statistics
				self.input_processed += 1
		# cache clearing requested?
		if self.clear_cache:
			self.cache.clearCache()
			self.clear_cache = False
		# reevaluate cache and delay times of modified events
		while len(self.modified_events) > 0:
			event = self.modified_events.pop()
			if event in self.cache.getEvents():
				self.cache.removeEventCacheAndDelayTime(event)
				self.rulemanager.updateCacheAndDelayTime(event)
				self.cache.insertEventCacheAndDelayTime(event)
		# advance ticker	
		self.ticker.advance()
