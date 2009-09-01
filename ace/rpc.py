#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Contains a class for RPC management.
"""

import select
from SimpleXMLRPCServer import SimpleXMLRPCServer
from threading import Thread

from ace.util import constants

class RPCHandler(Thread):
	"""
	Provides functions for RPCs.
	"""

	def __init__(self, config, logger, master, core):
		Thread.__init__(self)
		self.config = config
		self.logger = logger
		self.master = master
		self.core = core
		self.rpcserver = SimpleXMLRPCServer((self.config.rpcserver_host, self.config.rpcserver_port),
		                                    logRequests=False,
		                                    allow_none=True)
		self.rpcserver.register_function(self.getStats, "getStats")
		self.rpcserver.register_function(self.getContent, "getContent")
		self.rpcserver.register_function(self.execAction, "execAction")
		self.actions = {
		  "show_event": {'args': ['event'], 'function': self.execActionShowEvent},
		  "show_ruletable": {'args': [], 'function': self.execActionShowRuletable},
		  "show_querytable": {'args': [], 'function': self.execActionShowQuerytable},
		  "show_rulegroup": {'args': ['group'], 'function': self.execActionShowRulegroup},
		  "show_rule": {'args': ['group', 'rule'], 'function': self.execActionShowRule},
		  "show_context": {'args': ['group', 'name'], 'function': self.execActionShowContext},
		  "delete_context": {'args': ['group', 'name'], 'function': self.execActionDeleteContext},
		  "reload_rules": {'args': [], 'function': self.execActionReloadRules},
		  "clear_cache": {'args': [], 'function': self.execActionClearCache},
		  "show_inputqueue": {'args': [], 'function': self.execActionShowInputQueue},
		  "show_outputqueue": {'args': ["num"], 'function': self.execActionShowOutputQueue},
		}


	def getStats(self):
		"""
		Returns a list with statistics. Each item in the list is a tuple
		representing a key/value pair.
		"""
		return [
		    ("Current tick", self.master.ticker.getTick()),
		    ("Time running", self.master.ticker.getTimeRunningString()),
		    ("Processed input events", self.core.input_processed),
		    ("Generated output events", self.core.output_generated),
		    ("Events in input queue", self.master.input_queue.qsize()),
		    ("Events in output queues", str([q.qsize() for q in self.master.output_queues])),
		    ("Events in cache", len(self.core.cache.getEvents())),
		    ("Current number of contexts", self.core.contextmanager.getNumberOfContexts()),
		    ("Number of rules", self.core.rulemanager.getNumberOfRules()),
		    ("Average event processing rate", "%3.2f events per minute" % (self.core.processingRate()*60))
		]

	def getContent(self, page):
		"""
		Returns the content of the given page.
		
		@param page: string describing the page
		"""
		self.logger.logDebug("Returning RPC content for page '%s'." % page)
		if page == 'home':
			return [{
			  'title': "Welcome",
			  'type': "text",
			  'content': "This is ace running on %s." % self.config.hostname
			}]
		elif page == 'master':
			return self.master.getContent()
		elif page == 'core':
			return self.core.getContent()
		elif page == 'cache':
			return self.core.cache.getContent()
		elif page == 'contexts':
			return self.core.contextmanager.getContent()
		elif page == 'rulebase':
			return self.core.rulemanager.getContent()
		else:
			return [{'title': "No such page exists", 'type': "text", 'content': page}]

	def execAction(self, action, kwargs):
		"""
		Executes an RPC action and returns the content.
		
		@param action: action
		@type  action: string
		@param kwargs: arguments
		@type  kwargs: dict
		"""
		self.logger.logDebug("Executing RPC action '%s' with args %s." % (action, str(kwargs)))
		if action in self.actions.keys():
			needed_args = self.actions[action]['args']
			for arg in needed_args:
				if not kwargs.has_key(arg):
					return [{
					  'title': "Error in execAction",
					  'type': "text",
					  'content': "Action '%s' needs argument '%s'." % (action, arg)
					}]
			kwargs = dict([kwarg for kwarg in kwargs.iteritems() if kwarg[0] in needed_args])
			return self.actions[action]['function'](**kwargs)
		else:
			return [{
			  'title': "Error in execAction",
			  'type': "text",
			  'content': "No such action: %s" % action
			}]

	def execActionShowEvent(self, event):
		"""
		Returns content for an event.
		"""
		event = self.core.cache.getEventByID(event)
		if event == None:
			return [{
			  'title': "Error in execAction",
			  'type': "text",
			  'content': "No event with ID '%s' in cache." % event
			}]
		else:
			return event.getContent() + [{
			  'title': "Relevant rules",
			  'type': 'list',
			  'content': [rule.getLink() for rule in self.core.rulemanager.getRelevantRules(event)]
			}]

	def execActionShowRuletable(self):
		"""
		Returns content for the rule table.
		"""
		def rulecontent(rules):
			"""Helper function."""
			if len(rules) < 1:
				return ""
			elif len(rules) == 1:
				return rules[0].getLink()
			else:
				return reduce(lambda a, b: a+[", "]+b, [rule.getLink() for rule in rules])
		table = self.core.rulemanager.ruletable
		types = constants.EVENT_TYPES_ANY
		return [{
		  'title': "Rules for events with any name and given type",
		  'type': 'table',
		  'headers': ["Type", "Rules"],
		  'content': [[etype, rulecontent([rule[2] for rule in sorted(table.when_any[etype])])]
		              for etype in types]
		},{
		  'title': "Rules for events with given class and type",
		  'type': 'table',
		  'headers': ["Class", "Type", "Rules"],
		  'content': reduce(
		    lambda a, b: a + b,
		    [
		      [
		        [name, etype, rulecontent([rule[2]
		          for rule in sorted(table.when_class[name][etype])])]
		        for etype in types if len(table.when_class[name][etype]) > 0]
		      for name in table.when_class.keys()]
		  )
		},{
		  'title': "Rules for events with given name and type",
		  'type': 'table',
		  'headers': ["Name", "Type", "Rules"],
		  'content': reduce(
		    lambda a,b: a+b,
		    [
		      [
		        [name, etype, rulecontent([rule[2]
		          for rule in sorted(table.when_event[name][etype])])]
		        for etype in types if len(table.when_event[name][etype]) > 0]
		      for name in table.when_event.keys()]
		  )
		}]

	def execActionShowQuerytable(self):
		"""
		Returns content for the query table.
		"""
		headers = ["Rule", "Query name", "Max age", "Time source", "Delay?"]
		def limits_entry(entry, time_source, delay):
			""" Returns a table row with delay/cache limits. """
			return [entry['rule'].getLink() if entry['rule'] != None else "n/a",
			        entry['name'],
			        entry['max_age'],
			        time_source,
			        delay]
		table = self.core.rulemanager.querytable
		eventnames = set()
		for delay in [True, False]:
			for time_source in  ['creation', 'arrival']:
				eventnames.update(table[delay][time_source]['by_event'].keys())
		eventnames = list(eventnames)
		eventnames.sort()
		content = [{
		  'title': "Default delay and cache times for any event",
		  'type': 'table',
		  'headers': headers,
		  'content': [limits_entry(table[delay][time_source]['any'], time_source, delay)
		              for time_source in ['creation', 'arrival'] for delay in [True, False]]
		},{
		  'title': "Queries applicable to any event",
		  'type': 'table',
		  'headers': headers,
		  'content': [[qdet['rule'].getLink(), qdet['name'], qdet['max_age'], time_source, delay]
		              for delay in [True, False]
		              for time_source in ['creation', 'arrival']
		              for qdet in table[delay][time_source]['any']['qdets']]
		  }
		]
		for name in eventnames:
			content.append({
			  'title': "Default delay and cache times for '%s'" % name,
			  'type': 'table',
			  'headers': headers,
			  'content': [limits_entry(table[delay][time_source]['by_event'][name], time_source, delay)
			              for delay in [True, False]
			              for time_source in ['creation', 'arrival']
			              if table[delay][time_source]['by_event'].has_key(name)]
			})
			content.append({
			  'title': "Queries for event '%s'" % name,
			  'type': 'table',
			  'headers': headers,
			  'content': [[qdet['rule'].getLink(), qdet['name'], qdet['max_age'], time_source, delay]
			              for delay in [True, False]
			              for time_source in ['creation', 'arrival']
			              if table[delay][time_source]['by_event'].has_key(name)
			              for qdet in table[delay][time_source]['by_event'][name]['qdets']
			              if table[delay][time_source]['by_event'][name].has_key('qdets')]
			})
		return content

	def execActionShowRulegroup(self, group):
		"""
		Returns the content of a rule group.
		"""
		if self.core.rulemanager.hasGroup(group):
			group = self.core.rulemanager.getGroup(group)
			return group.getContent()
		else:
			return [{
			  'title': "No such group",
			  'type': "text",
			  'content': "RuleManager has no group '%s'." % group
			}]

	def execActionShowRule(self, group, rule):
		"""
		Returns the content for a single rule.
		"""
		if self.core.rulemanager.hasGroup(group):
			group = self.core.rulemanager.getGroup(group)
			if group.hasRule(rule):
				rule = group.getRule(rule)
				return rule.getContent()
			else:
				return [{
				  'title': "No such rule",
				  'type': "text",
				  'content': "Group '%s' has no rule '%s'." % (group, rule)
				}]
		else:
			return [{
			  'title': "No such group",
			  'type': "text",
			  'content': "RuleManager has no group '%s'." % group
			}]

	def execActionShowContext(self, group, name):
		"""
		Returns the content of a context.
		"""
		if self.core.contextmanager.hasGroup(group):
			group = self.core.contextmanager.getGroup(group)
			if group.has_key(name):
				context = group[name]
				return context.getContent()
			else:
				return [{
				  'title': "No such context",
				  'type': "text",
				  'content': "Group '%s' has no context '%s'." % (group, name)
				}]
		else:
			return [{
			  'title': "No such group",
			  'type': "text",
			  'content': "ContextManager has no group '%s'." % group
			}]

	def execActionDeleteContext(self, group, name):
		"""
		Asks the context manager to delete the specified context.
		"""
		if self.core.contextmanager.hasGroup(group):
			contextgroup = self.core.contextmanager.getGroup(group)
			if contextgroup.has_key(name):
				self.core.contextmanager.triggerDeleteContext(group, name)
				return [{
				  'title': "Context scheduled for deletion",
				  'type': "text",
				  'content': "Context '%s' in group '%s' will be deleted."\
				             % (name, group)
				}]
			else:
				return [{
				  'title': "No such context",
				  'type': "text",
				  'content': "Group '%s' has no context '%s'." % (group, name)
				}]
		else:
			return [{
			  'title': "No such group",
			  'type': "text",
			  'content': "ContextManager has no group '%s'." % group
			}]

	def execActionReloadRules(self):
		"""
		Asks the core to reload the rules.
		"""
		self.core.reloadRules()
		return [{
		  'title': "Rule reload",
		  'type': "text",
		  'content': "Reload of correlation rules has been triggered."
		}]

	def execActionClearCache(self):
		"""
		Asks the core to delete all events from the cache.
		"""
		self.core.triggerClearCache()
		return [{
		  'title': "Cache cleanup",
		  'type': "text",
		  'content': "Cleanup of event cache has been triggered."
		}]

	def execActionShowInputQueue(self):
		"""
		Returns the content for the events in the input queue.
		"""
		self.master.input_queue.mutex.acquire()
		content = [{
		  'title': "Events in input queue:",
		  'type': 'table',
		  'headers': ["Name", "Type", "Status", "Host", "Description", "Arrival"],
		  'content': [[
		    e.getName(),
		    e.getType(),
		    e.getStatus(),
		    e.getHost(),
		    e.getDescription(),
		    e.getArrivalTime(),
		  ] for e in sorted(self.master.input_queue.queue, key=lambda e:e.getArrivalTime())]
		}]
		self.master.input_queue.mutex.release()
		return content

	def execActionShowOutputQueue(self, num):
		"""
		Returns the content for the events in the output queue.
		
		@param num: queue number
		"""
		if not num.isdigit():
			return [{
			  'title': "Show output queue",
			  'type': "text",
			  'content': "No valid queue number: %s." % num
			}]
		qnum = int(num)
		if not qnum < len(self.master.output_queues):
			return [{
			  'title': "Show output queue",
			  'type': "text",
			  'content': "No such output queue: %d." % qnum
			}]
		self.master.output_queues[qnum].mutex.acquire()
		content = [{
		  'title': "Events in output queue %d:" % qnum,
		  'type': 'table',
		  'headers': ["Name", "Type", "Status", "Host", "Description", "Arrival"],
		  'content': [[
		    e.getName(),
		    e.getType(),
		    e.getStatus(),
		    e.getHost(),
		    e.getDescription(),
		    e.getArrivalTime(),
		  ] for e in sorted(self.master.output_queues[qnum].queue, key=lambda e:e.getArrivalTime())]
		}]
		self.master.output_queues[qnum].mutex.release()
		return content

	def run(self):
		"""
		Main thread function.
		"""
		self.logger.logInfo("Calling SimpleXMLRPCServer.serve_forever().")
		try:
			self.rpcserver.serve_forever()
		except select.error as e:
			self.logger.logErr("Calling of SimpleXMLRPCServer.serve_forever() failed: %s" % e)

	def shutdown(self):
		"""
		Stops the server.
		"""
		self.logger.logInfo("Calling SimpleXMLRPCServer.shutdown().")
		self.rpcserver.shutdown()
