#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Rule parsing and management.
"""

import hashlib
import re
import sys
from lxml import etree
from ace.util.exceptions import RuleParserException
from ace.util.constants import *
from ace.basisfunctions import rulecomponents
from ace.basisfunctions import querycomponents
from ace.event import MetaEvent

class NameRecord:
	"""
	Empty class used as name record object.
	"""
	def __init__(self):
		self.query_names = None
		self.query_classes = None
		self.trigger_names = None
		self.trigger_classes = None

class EventRecord:
	"""
	Empty class used as record for triggers.
	"""
	def __init__(self):
		self.when_any = None
		self.when_class = None
		self.when_event = None

class RuleManager:
	"""
	Manages the rules in the correlation engine.
	"""

	def __init__(self, config, logger):
		self.config = config
		self.logger = logger
		self.logger.logInfo("RuleManager: init.")
		self.ruleparser = RuleParser(config, logger)
		try:
			(self.rulegroups, self.names, self.query_determinators, self.named_queries) =\
			  self.ruleparser.parseRules(current=dict())
			self.logger.logInfo("Parsed %d rule groups." % len(self.rulegroups))
			self.eventclasses = self.ruleparser.parseEventClasses()
			self.logger.logInfo("Parsed %d event classes." % len(self.eventclasses))
		except (RuleParserException, IOError, etree.XMLSyntaxError) as e:
			self.logger.logErr("RuleManager: %s" % e)
			sys.exit(1)
		self.ruletable = self.buildRuletable()
		self.classtable = self.buildClasstable()
		self.querytable = self.buildQuerytable()

	def getNumberOfRules(self):
		return sum([len(group.rules) for group in self.rulegroups.values()])

	def getContent(self):
		"""
		Returns a content list for display in a UI.		
		"""
		return [
		  {
		    'title': "General information",
		    'type': 'list',
		    'content': [
		      "Number of groups: %d" % len(self.rulegroups),
		      "Total number of rules: %d" % self.getNumberOfRules()
		    ]
		  },{
		    'title': "Actions",
		    'type': 'list',
		    'content': [
		      [{'action': "show_ruletable", 'text': "Show rule table", 'args':{}}],
		      [{'action': "show_querytable", 'text': "Show query table", 'args':{}}]
		    ]
		  },{
		    'title': "Event classes",
		    'type': 'table',
		    'headers': ['Class name', 'Events'],
		    'content': [[name, ", ".join(self.eventclasses[name])] for name in self.eventclasses]
		  },{
		    'title': "Reverse event class table",
		    'type': 'table',
		    'headers': ['Event name', 'Classes'],
		    'content': [[name, ", ".join(self.classtable[name])] for name in self.classtable]
		  },{
		    'title': "Rule groups",
		    'type': 'table',
		    'headers': ["Name", "Order", "Description",  "Number of rules", "Execution count", "Actions"],
		    'content':
		      [[group.name, group.order, group.description,
		        len(group.rules), sum([r.exec_count for r in group.rules.values()]),
		        [{'action': "show_rulegroup", 'text': "show", 'args':{'group':group.name}}]
		       ] for group in sorted(self.rulegroups.values())]
		  }]+[{
		    'title': "Rules in group '%s'" % group.name,
		    'type': "table",
		    'headers': ["Name", "Order", "Description", "Execution count", "Actions"],
		    'content':
		      [[rule.name, rule.order, rule.description, rule.exec_count,
		        [{'action': "show_rule", 'text': "show", 'args':{'group':group.name ,'rule': rule.name}}]
		       ] for rule in sorted(group.rules.values(), key=lambda rule: rule.order)]
		  } for group in sorted(self.rulegroups.values())]+[{
		    'title': "Queries",
		    'type': "table",
		    'headers': ["Rule name", "Query name", "Max age", "Time source", "Delay"],
		    'content': [[qdet['rule'].getLink(),
		                 qdet['name'],
		                 qdet['max_age'],
		                 qdet['time_source'],
		                 qdet['delay']
		                ] for qdet in self.query_determinators]
		  }
		]

	def reloadRules(self):
		"""
		Tries to reload to rules.
		 - old groups are deleted and their contexts are removed
		 - if a rulegroup is not changed (or only comments and whitespace were
		   changed), the old rule is kept
		"""
		try:
			self.ruleparser.resetState()
			(newrules, names, qdets, named_queries) = self.ruleparser.parseRules(current=self.rulegroups)
			self.eventclasses = self.ruleparser.parseEventClasses()
		except (RuleParserException, IOError, etree.XMLSyntaxError) as e:
			self.logger.logErr(str(e))
			self.logger.logErr("Keeping current correlation rules.")
			return []
		changedgroups = [] # groups, whose contexts need to be deleted
		for group in self.rulegroups.keys():
			if not group in newrules.keys():
				self.logger.logInfo("Rule group %s no longer exists." % group)
			elif self.rulegroups[group].getHash() != newrules[group].getHash():
				self.logger.logInfo("Removing contexts of modified rule group %s." % group)
				changedgroups.append(group)
		self.rulegroups = newrules
		self.names = names
		self.query_determinators = qdets
		self.named_queries = named_queries
		self.ruletable = self.buildRuletable()
		self.logger.logNotice("RuleManager: new rule table built.")
		self.classtable = self.buildClasstable()
		self.logger.logNotice("RuleManager: new table built.")
		self.querytable = self.buildQuerytable()
		self.logger.logNotice("RuleManager: new query table built.")
		return changedgroups

	def getRelevantRules(self, event):
		"""
		Returns the relevant rules for the given event in the correct order for execution.
		
		@param event: trigger event
		"""
		relevant_rules = []
		# rules with when_any
		relevant_rules.extend(self.ruletable.when_any['any'])
		relevant_rules.extend(self.ruletable.when_any[event.getType()])
		# rules with matching when_class
		classes = self.getEventClasses(event)
		for class_ in classes:
			if class_ in self.ruletable.when_class:
				relevant_rules.extend(self.ruletable.when_class[class_]['any'])
				relevant_rules.extend(self.ruletable.when_class[class_][event.getType()])
		# rules with matching when_event
		if event.getName() in self.ruletable.when_event:
			relevant_rules.extend(self.ruletable.when_event[event.getName()]['any'])
			relevant_rules.extend(self.ruletable.when_event[event.getName()][event.getType()])
		# make unique, sort, return
		relevant_rules = list(set(relevant_rules)) # to make sure the list contains each rule at most once
		relevant_rules.sort()
		return [entry[2] for entry in relevant_rules]

	def updateCacheAndDelayTime(self, event):
		"""
		Update the events cache and delay time according to the query table.
		
		@param event: Event instance
		"""
		name = event.getName()
		for delay in [True, False]:
			max_time = 0
			rule = None
			relevant_queries = []
			for time_source in ['creation', 'arrival']:
				eventtime = event.getTimestamp(time_source)
				# relevant_queries += self.querytable[delay][time_source]['any']['qdets']
				entries = [self.querytable[delay][time_source]['any']]
				if self.querytable[delay][time_source]['by_event'].has_key(name):
					entries += [self.querytable[delay][time_source]['by_event'][name]]
				for entry in entries:
					if entry['max_age'] + eventtime > max_time:
						max_time = entry['max_age'] + eventtime
						rule = entry['rule']
					relevant_queries.extend([(det['max_age'] + eventtime, det) for det in entry['qdets']])
			relevant_queries.sort(reverse=True)
			for (cur_max, qdet) in relevant_queries:
				if cur_max <= max_time:
					break
				else:
					if qdet['determinator'](event=event, rulemanager=self) != False:
						max_time = qdet['max_age'] + eventtime
						rule = qdet['rule']
			# brute force solution
			if DEBUG:
				bfsolution = max(event.getCreationTime(), event.getArrivalTime())
				for qdet in self.query_determinators:
					eventtime = event.getTimestamp(qdet['time_source'])
					if qdet['delay'] == delay:
						if qdet['max_age'] + eventtime > bfsolution:
							if qdet['determinator'](event=event, rulemanager=self) != False:
								bfsolution = qdet['max_age'] + eventtime
				if bfsolution != max_time:
					self.logger.logWarn(
					  "RuleManager: updateCacheAndDelayTime: Discrepancy - brute force result: "\
					 +"%d table result: %d (delay: %s, rule: %s)."\
					 %(bfsolution, max_time, str(delay), rule))
			# update event timestamp and rule
			if delay:
				event.setDelayTime(max_time, rule)
			else:
				event.setCacheTime(max_time, rule)

	def getEventClasses(self, event):
		name = event.getName()
		if name in self.classtable:
			return self.classtable[name]
		else:
			return set()

	def buildRuletable(self):
		"""
		Builds a table with the relevant rules for each event name/type
		combination. The rules in the table are ordered according to priority
		for each event.
		"""
		self.logger.logInfo("RuleManager: building rule table.")
		ruletable = EventRecord()
		ruletable.when_any = dict([(event_type, []) for event_type in EVENT_TYPES_ANY])
		ruletable.when_class = dict(
		  [(event_class, dict([(event_type, []) for event_type in EVENT_TYPES_ANY]))
		    for event_class in self.names.trigger_classes])
		ruletable.when_event = dict(
		  [(event_name, dict([(event_type, []) for event_type in EVENT_TYPES_ANY]))
		    for event_name in self.names.trigger_names])
		for group in sorted(self.rulegroups.values()):
			for rule in sorted(group.rules.values()):
				ruletuple = (group.order, rule.order, rule)
				types = EVENT_TYPES[:]
				# when_any
				if 'any' in rule.events.when_any: # rule always triggers (any event/any type)
					ruletable.when_any['any'].append(ruletuple)
					continue
				for eventtype in EVENT_TYPES:
					if eventtype in rule.events.when_any:
						ruletable.when_any[eventtype].append(ruletuple)
						types.remove(eventtype)
				# when_class
				for class_ in rule.events.when_class:
					if 'any' in rule.events.when_class[class_]: # specific class / any type
						ruletable.when_class[class_].append(ruletuple)
						continue
					for eventtype in types:
						if eventtype in rule.events.when_class[class_]: # specific class and type
							ruletable.when_class[class_][eventtype].append(ruletuple)
				# when_event
				for event in rule.events.when_event:
					if 'any' in rule.events.when_event[event]: # specific name / any type
						ruletable.when_event[event].append(ruletuple)
						continue
					for eventtype in types:
						if eventtype in rule.events.when_event[event]: # specific name and type
							ruletable.when_event[event][eventtype].append(ruletuple)
		return ruletable

	def buildClasstable(self):
		"""
		Builds a reverse lookup table with classes for a given event name.
		"""
		classtable = dict()
		for eventclass in self.eventclasses:
			for eventname in self.eventclasses[eventclass]:
				if not classtable.has_key(eventname):
					classtable[eventname] = set()
				classtable[eventname].add(eventclass)
		return classtable

	def buildQuerytable(self): # Note: requires verification
		"""
		Builds a lookup table to find relevant queries for a given event.
		"""
		# query table: 1. key: delay, 2. key: time_source 3. key: criteria
		qtable = {}
		for delay in [True, False]:
			qtable[delay] = {}
			for time_source in ['creation', 'arrival']:
				qtable[delay][time_source] = {}
				qtable[delay][time_source]['any'] = {'max_age': 0, 'rule': None, 'name': "n/a", 'qdets': []}
				qtable[delay][time_source]['by_event'] = {}
		# all names, which appear directly in a query, or via an event class:
		eventnames = set.union(self.names.query_names, self.classtable.keys()).union(set([None]))
		# build the table
		for qdet in self.query_determinators:
			qname = qdet['name']
			longname = "%s::%s" % (qdet['rule'], qname)
			det = qdet['determinator']
			max_age = qdet['max_age']
			delay = qdet['delay']
			time_source = qdet['time_source']
			rule = qdet['rule']
			if det(predetermined_fields={'default': UNDEFINED}) == False:
				# independently of the event fields, this query *never*
				# delays/caches an event
				self.logger.logDebug("Query %s always false - ignoring." % longname)
			elif det(predetermined_fields={'default': UNDEFINED}) == True:
				# independently of the event fields, this query *always*
				# delays or caches an event (such queries should be avoided,
				# because they keep all events back; the advantage on the other
				# hand is that we only have to store the largest cache and
				# delay times)
				if max_age > qtable[delay][time_source]['any']['max_age']:
					qtable[delay][time_source]['any']['max_age'] = max_age
					qtable[delay][time_source]['any']['rule'] = rule
					qtable[delay][time_source]['any']['name'] = qname
					self.logger.logDebug("Query %s always true - extending global max." % longname)
				else:
					self.logger.logDebug("Query %s always true, but max_age < global max." % longname)
			elif det(predetermined_fields={'default': DEFINED}) == UNDEFINED:
				# query is undefined even with all event info available -> we
				# have to delay / cache all events due to this query
				if max_age > qtable[delay][time_source]['any']['max_age']:
					qtable[delay][time_source]['any']['max_age'] = max_age
					qtable[delay][time_source]['any']['rule'] = rule
					qtable[delay][time_source]['any']['name'] = qname
					self.logger.logDebug("Query %s always undefined - extending global max." % longname)
				else:
					self.logger.logDebug("Query %s always undefined, but max_age < global max." % longname)
			else:
				assert(det(predetermined_fields={'default': DEFINED}) == DEFINED)
				# we can decide according to event info
				predet = {'default': UNDEFINED, 'event_name': False, 'event_class': False}
				if det(predetermined_fields=predet) == False:
					# this query is relevant only for some given (matching)
					# event names. this is good and should ideally be the case
					# for many queries
					self.logger.logDebug("Query %s applies to specific names/classes only." % longname)
					predet = {
					  'in_context': UNDEFINED,
					  'event_host': UNDEFINED,
					  'event_attribute': UNDEFINED,
					  'event_status': UNDEFINED,
					  'event_type': UNDEFINED
					}
					for name in eventnames:
						val = det(event=MetaEvent(name=name), predetermined_fields=predet, rulemanager=self)
						assert(val == True or val == False or val == UNDEFINED)
						if val != False:
							self.logger.logDebug("Query %s applies to %s." % (longname, name))
							if not qtable[delay][time_source]['by_event'].has_key(name):
								qtable[delay][time_source]['by_event'][name] = \
								  {'max_age': 0, 'rule': None, 'name': "n/a", 'qdets': []}
							if val == True: # store value
								if max_age > qtable[delay][time_source]['by_event'][name]['max_age']:
									qtable[delay][time_source]['by_event'][name]['max_age'] = max_age
									qtable[delay][time_source]['by_event'][name]['rule'] = rule
									qtable[delay][time_source]['by_event'][name]['name'] = qname
							elif val == UNDEFINED: # store query
								qtable[delay][time_source]['by_event'][name]['qdets'].append(qdet)
				else: # decidable according to event info, but name is irrelevant
					qtable[delay][time_source]['any']['qdets'].append(qdet)
		# delete all queries that have become irrelevant, because the default
		# max_age is larger, and sort the queries by max_age (largest last)
		for delay in [True, False]:
			for time_source in ['creation', 'arrival']:
				max_age_any = qtable[delay][time_source]['any']['max_age']
				entries = [qtable[delay][time_source]['any']]\
				          +qtable[delay][time_source]['by_event'].values()
				for entry in entries:
					max_age = max(entry['max_age'], max_age_any)
					qdets = [qdet for qdet in entry['qdets'] if qdet['max_age'] > max_age]
					qdets.sort(key = lambda qdet: qdet['max_age'])
					entry['qdets'] = qdets
				for item in qtable[delay][time_source]['by_event'].iteritems():
					if len(item[1]['qdets']) == 0 and item[1]['max_age'] < max_age_any:
						qtable[delay][time_source]['by_event'].remove(item[0])
		return qtable

	def hasGroup(self, group):
		"""
		Checks, whether a rulegroup with the given name exists in the rule
		manager.
		
		@param group: group name
		"""
		return self.rulegroups.has_key(group)

	def getGroup(self, group):
		if self.rulegroups.has_key(group):
			return self.rulegroups[group]
		else:
			return None
	
	def getRule(self, group, rule):
		group = self.getGroup(group)
		if group != None:
			return group.getRule(rule)
		else:
			return None

	def getNamedQuery(self, group, name):
		return self.named_queries[group][name][0]

	def getNamedQueryDeterminator(self, group, name):
		return self.named_queries[group][name][1]

class RuleGroup:
	"""
	Represents a single rule group.
	"""
	def __init__(self, config, logger, name, order, grouphash, description=""):
		self.config = config
		self.logger = logger
		self.name = name
		self.order = order
		self.grouphash = grouphash
		self.description = description
		self.rules = {}

	def getLink(self):
		return [{
		  'action': "show_rulegroup",
		  'text': self.group.name,
		  'args': {'group': self.group.name}
		}]

	def getContent(self):
		return [
		  {
		    'title': "General rule group information",
		    'type': 'list',
		    'content': [
		      "Group name: %s" % self.name,
		      "Order: %d" % self.order,
		      "Description: %s" % self.description,
		      "Hash: %s" % self.getHash(),
		      "Execution count (sum of rule executions): %d"\
		        % sum([r.exec_count for r in self.rules.values()])
		    ]
		  },{
		    'title': "Rules",
		    'type': "table",
		    'headers': ["Name", "Order", "Description", "Execution count", "Action"],
		    'content': [[
		      rule.name,
		      rule.order,
		      rule.description,
		      rule.exec_count,
		      [{
		        'action': "show_rule",
		        'text': "show",
		        'args': {'group': rule.group.name ,'rule': rule.name}
		      }]
		    ] for rule in sorted(self.rules.values())]
		  }
		]

	def addRule(self, rule):
		"""
		Adds the given rule to the rulegroup.
		
		@param rule: Rule instance
		@type  rule: Rule
		"""
		self.rules[rule.name] = rule

	def hasRule(self, rule):
		"""
		Checks whether the rule group has a rule with the given name.
		
		@param rule: rule name
		@type  rule: string
		"""
		return self.rules.has_key(rule)

	def getRule(self, rule):
		if self.rules.has_key(rule):
			return self.rules[rule]
		else:
			return None

	def getHash(self):
		return self.grouphash

class Rule:
	"""
	Represents a single rule.
	"""
	def __init__(self, group, name, order, description, events, condition,
	             actions, alternative_actions, ruletext):
		self.group = group
		self.name = name
		self.order = order
		self.description = description
		self.events = EventRecord()
		self.events.when_any = events[TAG_WHEN_ANY]
		self.events.when_event = events[TAG_WHEN_EVENT]
		self.events.when_class = events[TAG_WHEN_CLASS]
		self.condition = condition
		self.actions = actions
		self.alternative_actions = alternative_actions
		self.ruletext = ruletext
		self.exec_count = 0
		self.exec_count_true = 0
		self.exec_count_false = 0

	def __str__(self):
		return self.group.name+"::"+self.name

	def getLink(self):
		return [
		  {
		    'action': "show_rulegroup",
		    'text': self.group.name,
		    'args':{'group': self.group.name}
		  }, "::", {
		    'action': "show_rule",
		    'text': self.name,
		    'args':{'group': self.group.name, 'rule': self.name}
		  }
		]

	def getContent(self):
		return [
		  {
		    'title': "General rule information",
		    'type': 'list',
		    'content': [
		      [ "Group name: ",
		        {
		          'action': "show_rulegroup",
		          'text': self.group.name,
		          'args': {'group': self.group.name}
		        }],
		      "Rule name: %s" % self.name,
		      "Order: %d" % self.order,
		      "Description: %s" % self.description,
		      "Execution count (total): %d" % self.exec_count,
		      "Execution count (conditions true): %d" % self.exec_count_true,
		      "Execution count (conditions false): %d" % self.exec_count_false
		    ]
		  },{
		    'title': "Triggers",
		    'type': 'table',
		    'headers': ["Trigger type", "Name", "Event types"],
		    'content':
		      [["when_any", "-", ", ".join(self.events.when_any)]
		        if len(self.events.when_any)>0 else []]+
		      [["when_class", item[0], ", ".join(item[1])]
		        for item in self.events.when_class.iteritems()]+
		      [["when_event", item[0], ", ".join(item[1])]
		        for item in self.events.when_event.iteritems()]
		  }
		]+[{
		    'title': "Reconstructed content of '%s' element" % entry[0],
		    'type': 'pre',
		    'content': entry[1]
		  } for entry in self.ruletext]

	def execute(self, trigger, core, rulemanager, cache, contexts):
		"""
		Executes this rule with the given trigger, core, cache and contexts.
		
		@param trigger: trigger event
		@param core: reference to core
		@type  core: EventHandler
		@param cache: reference to the cache
		@type  cache: EventCache
		@param contexts: reference to the context manager
		@type  contexts: ContextManager
		"""
		self.exec_count += 1
		kwargs = {'rule': self, 'trigger': trigger, 'core': core, 'rulemanager': rulemanager,
		          'cache': cache, 'contexts': contexts, 'selected_events': [trigger]}
		if self.condition(**kwargs):
			self.group.logger.logDebug("Rule condition true -> executing actions.")
			self.exec_count_true += 1
			for action in self.actions:
				action(**kwargs)
		else:
			self.group.logger.logDebug("Rule condition false -> executing alternative actions.")
			self.exec_count_false += 1
			for action in self.alternative_actions:
				action(**kwargs)

class RuleParser:
	"""
	Parses the XML rules.
	"""
	def __init__(self, config, logger):
		self.config = config
		self.logger = logger
		self.parser = etree.XMLParser(attribute_defaults=True,
		                              dtd_validation=True,
		                              load_dtd=True,
		                              remove_comments=True,
		                              remove_blank_text=True)
		self.parse_errors = []
		self.named_queries = {}
		self.query_references = {}
		self.query_determinators = []
		self.currentgroup = None
		self.currentrule = None
		self.currentquery = None
		self.components = rulecomponents

	def resetState(self):
		"""
		Get ready to parse new rules.
		"""
		self.parse_errors = []
		self.named_queries = {}
		self.query_references = {}
		self.query_determinators = []
		self.currentgroup = None
		self.currentrule = None
		self.components = rulecomponents

	def detectQueryLoops(self, referenced_so_far, group, query):
		"""
		Recursively verifies, whether there are loops with match_query.
		
		@param referenced_so_far: list with query calls so far
		@param group: current rule group name (string)
		@param query: next query to check
		"""
		for reference in self.query_references[group][query]:
			if not self.query_references[group].has_key(reference):
				self.parsingError("Referenced query not found in query '%s': '%s'"
				                  % ('[unnamed query]' if query==None else query, reference))
				break
			if reference in referenced_so_far:
				self.parsingError("Query loop detected (with match_query): %s"\
				                  % (referenced_so_far+[query, reference]))
				break
			else:
				self.detectQueryLoops(referenced_so_far+[query], group, reference)

	def parseRules(self, current):
		"""
		Parse the rules from the rule file - the lxml etree parser generates a
		tree with iterable nodes.
		
		@param current: current rulegroups 
		"""
		config = self.config.rulesource.split(":")
		source = config[0]
		if len(config)>1:
			options = dict([kv.split('=') for kv in config[1:] if kv.find('=')>=0])
		else:
			options = dict()
		if source == 'file':
			if not options.has_key('filename'):
				raise RuleParserException("'file' rulesource needs option 'filename'.")
			else:
				rules = etree.parse(options['filename'], self.parser)
		else:
			raise RuleParserException("Unknown rule source '%s'." % source)
		root = rules.getroot()
		# check root tag
		if root.tag != TAG_ROOT:
			raise RuleParserException("Unexpected root tag '%s'." % root.tag)
		# get event names end classes
		names = NameRecord()
		names.trigger_classes = set([str(i) for i in root.xpath("//when_class/text()")])
		names.trigger_names = set([str(i) for i in root.xpath("//when_event/text()")])
		names.query_classes = set([str(i) for i in root.xpath("//event_query//event_class/text()")])
		names.query_names = set([str(i) for i in root.xpath("//event_query//event_name/text()")])
		event_queries = root.xpath("//event_query")
		# log for debugging
		self.logger.logDebug("Got "+str(len(names.trigger_classes))+" trigger event classes.")
		self.logger.logDebug("Got "+str(len(names.trigger_names))+" trigger event names.")
		self.logger.logDebug("Got "+str(len(names.query_classes))+" query event classes.")
		self.logger.logDebug("Got "+str(len(names.query_names))+" query event names.")
		self.logger.logDebug("Got "+str(len(event_queries))+" event queries.")
		# parse the rule groups
		groups = dict()
		for group in root:
			self.currentgroup = group.attrib['name']
			self.currentrule = "n/a"
			# make sure the group names are unique
			if group.attrib['name'] in groups.keys():
				self.parsingError("Duplicate group name: %s" % group.attrib['name'])
			# make sure the group orders are unique
			if group.attrib['order'].strip() in [str(g.order) for g in groups.values()]:
				self.parsingError("Duplicate group order: %s" % group.attrib['order'])
			# if ok, parse the group
			groups[group.attrib['name']] = self.parseGroup(group, current)
		# replace (group name, rule name) in query determinators by reference to actual rule
		for qdet in self.query_determinators:
			group = qdet['rule'][0]
			rule = qdet['rule'][1]
			qdet['rule'] = groups[group].getRule(rule)
		# sanity check for referenced queries (existence + no loops)
		for group in self.query_references:
			self.currentgroup = group
			self.currentrule = "n/a"
			for query in self.query_references[group]:
				self.detectQueryLoops([], group, query)
		if len(self.getParsingErrors()) > 0:
			for error in self.getParsingErrors():
				self.logger.logErr("Error in group '%s', rule '%s': %s" % error)
			raise RuleParserException("There were %d errors." % len(self.getParsingErrors()))
		else:
			return (groups, names, self.query_determinators, self.named_queries)

	def parseEventClasses(self):
		"""
		Parses the event classes from the class file.
		"""
		if self.config.classlist == '':
			return dict()
		config = self.config.classlist.split(":")
		source = config[0]
		if len(config)>1:
			options = dict([kv.split('=') for kv in config[1:] if kv.find('=')>=0])
		else:
			options = dict()
		if source == 'file':
			if not options.has_key('filename'):
				raise RuleParserException("'file' classlist source needs option 'filename'.")
			else:
				classlist = etree.parse(options['filename'], self.parser)
		else:
			raise RuleParserException("Unknown classlist source '%s'." % source)
		root = classlist.getroot()
		# check root tag
		if root.tag != CLASSLIST_ROOT:
			raise RuleParserException("Unexpected root tag for class list '%s'." % root.tag)
		classes = dict()
		for eventclass in root:
			classes[eventclass.attrib['name']] = set()
			for eventname in eventclass:
				classes[eventclass.attrib['name']].add(eventname.text)
		return classes

	def parsingError(self, what):
		"""
		Adds an entry to the error list.
		"""
		self.parse_errors.append((self.currentgroup, self.currentrule, what))

	def getParsingErrors(self):
		return self.parse_errors

	def parseGroup(self, group, current):
		"""
		Parse a single rule group. If the group is old (a group with the same
		hash exists), the old group is reused.
		
		@param group: lxml Element with group content
		@param current: current groups
		"""
		assert(group.tag == TAG_GROUP)
		# check if group already exists
		newhash = hashlib.sha256(etree.tostring(group, pretty_print=True)).hexdigest()
		if newhash in [g.grouphash for g in current.values()]:
			self.logger.logDebug("Keeping unchanged rule group: ", group.attrib['name'])
			return [g for g in current.values() if g.grouphash == newhash][0]
		# get group name, order and description
		name = group.attrib['name']
		if not group.attrib['order'].isdigit():
			self.parsingError("Group order is not an integer: %s" % group.attrib['order'])
			group.attrib['order'] = '0' # workaround -> keep parsing to possibly detect more errors
		order = int(group.attrib['order'])
		if group.attrib.has_key('description'):
			description = group.attrib['description']
		else:
			description = ""
		# create the rulegroup
		rulegroup = RuleGroup(self.config, self.logger, name, order, newhash, description)
		# parse the rules
		for rule in group:
			# make sure the rule names are unique
			if rule.attrib['name'] in rulegroup.rules.keys():
				self.parsingError("Duplicate rule name: %s" % rule.attrib['name'])
			# make sure the rule orders are unique
			if rule.attrib['order'] in [str(r.order) for r in rulegroup.rules.values()]:
				self.parsingError("Duplicate rule order: %s" % rule.attrib['order'])
			rulegroup.addRule(self.parseRule(rulegroup, rule))
		return rulegroup

	def parseRule(self, group, rule):
		"""
		Parses a single rule.
		
		@param group: the enclosing group
		@param rule: an lxml Element with the rule
		"""
		assert(rule.tag == TAG_RULE)
		# get rule name, order and description
		name = rule.attrib['name']
		if not rule.attrib['order'].isdigit():
			self.parsingError("Rule order is not an integer: %s" % rule.attrib['order'])
			rule.attrib['order'] = '0' # just so we can keep parsing, and possibly detect more errors
		order = int(rule.attrib['order'])
		if rule.attrib.has_key('description'):
			description = rule.attrib['description']
		else:
			description = ""
		# parse the rule
		self.currentrule = name
		rulecontent = {TAG_EVENTS: None, TAG_CONDITIONS:[], TAG_ACTIONS:[], TAG_ALTERNATIVE_ACTIONS:[]}
		ruletext = []
		for child in rule:
			rulecontent[child.tag] = self.parseRuleElement(child)
			ruletext.append((child.tag, etree.tostring(child, pretty_print=True)))
		events = rulecontent[TAG_EVENTS]
		condition = self.components.and_(rulecontent[TAG_CONDITIONS])
		actions = rulecontent[TAG_ACTIONS]
		alternative_actions = rulecontent[TAG_ALTERNATIVE_ACTIONS]
		return Rule(group, name, order, description, events, condition,
		            actions, alternative_actions, ruletext)

	def parseTime(self, timestr):
		"""
		Parse a timestring and return the time value in seconds (e.g. 10m -> 600).
		
		@param timestr: a string in the format \d+[dhms]?, where d, h, m and s
		stands for days, hours, minutes and seconds respectively, with seconds
		being the default
		"""
		if not re.match("\d+[dhms]?", timestr):
			self.parsingError("Invalid time format: %s" % timestr)
			return 0
		if timestr.isdigit():
			return int(timestr)
		elif timestr[-1]=='d':
			return 24*3600*int(timestr[:-1])
		elif timestr[-1]=='h':
			return 3600*int(timestr[:-1])
		elif timestr[-1]=='m':
			return 60*int(timestr[:-1])
		else:
			return int(timestr[:-1])

	def parseInt(self, string):
		"""
		Tries to convert the string to an integer and adds an entry to the
		error list, if that isn't possible.
		"""
		if not string.isdigit():
			self.parsingError("Integer value expected: %s" % string)
			return 0 # workaround, so we can keep parsing
		else:
			return int(string)

	def parseMixedContent(self, element):
		"""
		Returns a function, which will generate the correct string when text is
		intermixed with the <trigger> element.
		"""
		children = []
		for child in element:
			childfunc = self.parseRuleElement(child)
			if child.tail == None:
				children.append(childfunc)
			else:
				children.append(lambda **kwargs: childfunc(**kwargs)+child.tail)
		return self.components.mixed_content(element.text, children)

	def parseRuleElement(self, element):
		"""
		Parses the given XML element recursively and builds the rule.
		
		@param element: an XML element
		@type  element: lxml elementtree.ElementTree.Element
		"""
		if element.tag == TAG_EVENTS:
			events = {TAG_WHEN_ANY: set(), TAG_WHEN_CLASS: dict(), TAG_WHEN_EVENT: dict()}
			for child in element:
				if child.tag == TAG_WHEN_ANY:
					events[child.tag].update(self.parseRuleElement(child))
				else:
					(name, types) = self.parseRuleElement(child)
					if not events[child.tag].has_key(name):
						events[child.tag][name] = set()
					events[child.tag][name].update(types)
			return events
		elif element.tag == TAG_CONDITIONS:
			conditions = []
			for child in element:
				conditions.append(self.parseRuleElement(child))
			return conditions
		elif element.tag == TAG_ACTIONS or element.tag == TAG_ALTERNATIVE_ACTIONS:
			actions = []
			for child in element:
				actions.append(self.parseRuleElement(child))
			return actions
		elif element.tag == TAG_WHEN_ANY:
			if element.attrib.has_key('type'):
				types = element.attrib['type'].split("|")
			else:
				types = ["raw", "compressed"]
			if not set(types).issubset(set(EVENT_TYPES+['any'])):
				self.parsingError("Invalid event types: %s" % str(types))
			return types
		elif element.tag == TAG_WHEN_CLASS or element.tag == TAG_WHEN_EVENT:
			if element.attrib.has_key('type'):
				types = element.attrib['type'].split("|")
			else:
				types = ["raw", "compressed"]
			if not set(types).issubset(set(EVENT_TYPES+['any'])):
				self.parsingError("Invalid event types: %s" % str(types))
			return (element.text.strip(), types)
		elif element.tag == TAG_AND:
			conditions = []
			for child in element:
				conditions.append(self.parseRuleElement(child))
			return self.components.and_(conditions)
		elif element.tag == TAG_OR:
			conditions = []
			for child in element:
				conditions.append(self.parseRuleElement(child))
			return self.components.or_(conditions)
		elif element.tag == TAG_NOT:
			assert(len(element)==1) # again, should always true because of DTD
			return self.components.not_(self.parseRuleElement(element[0]))
		elif element.tag == TAG_CONTEXT:
			namefunc = self.parseMixedContent(element)
			if element.attrib.has_key('group'):
				group = element.attrib('group')
			else:
				group = self.currentgroup
			if element.attrib.has_key('counter'):
				counter_val = self.parseInt(element.attrib['counter'])
				return self.components.context(group,
				                               namefunc,
				                               counter_val=counter_val,
				                               op=element.attrib['counter_op'])
			else:
				return self.components.context(group, namefunc)
		elif element.tag == TAG_TRIGGER_MATCH:
			conditions = []
			for child in element:
				conditions.append(self.parseRuleElement(child))
			return self.components.trigger_match(conditions)
		elif element.tag == TAG_COUNT:
			threshold = self.parseInt(element.attrib['threshold'])
			op = element.attrib['op']
			assert(op=="eq" or op=="le" or op=="ge")
			query = self.parseRuleElement(element[0])
			return self.components.count(threshold, op, query)
		elif element.tag == TAG_SEQUENCE:
			queries = []
			for child in element:
				queries.append(self.parseRuleElement(child))
			return self.components.sequence(element.attrib['sort_by'], element.attrib['match'], queries)
		elif element.tag == TAG_PATTERN:
			assert(element[0].tag == TAG_ALPHABET)
			assert(element[1].tag == TAG_REGEXP)
			assert(len(element)==2)
			alphabet = self.parseRuleElement(element[0])
			regexp = self.parseRuleElement(element[1])
			return self.components.pattern(alphabet, regexp)
		elif element.tag == TAG_ALPHABET:
			sort_by = element.attrib['sort_by']
			assert(sort_by == "creation" or sort_by == "arrival")
			symbols = []
			for child in element:
				symbols.append(self.parseRuleElement(child))
			return self.components.alphabet(sort_by, symbols)
		elif element.tag == TAG_SYMBOL:
			assert(len(element)==1)
			assert(element[0].tag == TAG_EVENT_QUERY)
			if len(element.attrib['letter'])!=1:
				self.parsingError("Error in element %s: Attribute 'letter' must have length 1." % element.tag)
			letter = element.attrib['letter'][0]
			query = self.parseRuleElement(element[0])
			return self.components.symbol(letter, query)
		elif element.tag == TAG_REGEXP:
			try:
				return self.components.regexp(element.text.strip())
			except re.error as e:
				self.parsingError("Error compiling regular expression for tag 'regexp': %s" % e)
				return None
		elif element.tag == TAG_WITHIN:
			queries = []
			for child in element:
				queries.append(self.parseRuleElement(child))
			timeframe = self.parseTime(element.attrib['timeframe'])
			return self.components.within(timeframe,
			                              element.attrib['timeref'],
			                              element.attrib['match'],
			                              queries)
		elif element.tag == TAG_CONDITION_PLUGIN:
			parameters = {}
			queries = []
			for child in element:
				if child.tag == TAG_EVENT_QUERY:
					queries.append(self.parseRuleElement(child))
				elif child.tag == TAG_PLUGIN_PARAMETER:
					parameters[child.attrib['name']] = self.parseRuleElement(child)
			return self.components.condition_plugin(self.config,
			                                        self.logger,
			                                        element.attrib['name'],
			                                        parameters,
			                                        queries)
		elif element.tag == TAG_PLUGIN_PARAMETER:
			return element.text.strip()
		elif element.tag == TAG_SUBBLOCK:
			subblock_content = {TAG_CONDITIONS:[], TAG_ACTIONS:[], TAG_ALTERNATIVE_ACTIONS:[]}
			for child in element:
				subblock_content[child.tag] = self.parseRuleElement(child)
			return self.components.if_then_else(
			  self.components.and_(subblock_content[TAG_CONDITIONS]),
			  subblock_content[TAG_ACTIONS],
			  subblock_content[TAG_ALTERNATIVE_ACTIONS]
			)
		elif element.tag == TAG_SELECT_EVENTS:
			actions = []
			for child in element:
				if child.tag == TAG_EVENT_QUERY:
					assert(element.index(child)==0) # only first child is a query
					query = self.parseRuleElement(child)
				else:
					actions.append(self.parseRuleElement(child))
			return self.components.select_events(query, actions)
		elif element.tag == TAG_DROP:
			return self.components.drop
		elif element.tag == TAG_FORWARD:
			return self.components.forward
		elif element.tag == TAG_COMPRESS:
			return self.components.compress
		elif element.tag == TAG_AGGREGATE:
			assert(len(element)==1)
			event = self.parseRuleElement(element[0])
			return self.components.aggregate(event[0], event[1])
		elif element.tag == TAG_MODIFY:
			status = element.attrib['status'] if element.attrib.has_key('status') else None
			local = (element.attrib['local']=="true") if element.attrib.has_key('local') else None
			reason = element.attrib['reason'] if element.attrib.has_key('reason') else None
			if status != None:
				assert(status in EVENT_STATUSES)
			if local == None and status == None:
				self.parsingError("'modify' doesn't modify anything.")
			rule = {'groupname': self.currentgroup, 'rulename': self.currentrule}
			return self.components.modify(status, local, rule, reason)
		elif element.tag == TAG_MODIFY_ATTRIBUTE:
			value = element.text.strip()
			op = element.attrib['op'].lower()
			if not (op == 'set' or ((op in ['inc', 'dec']) and value.isdigit())):
				self.parsingError("'op' must be 'set', 'inc' or 'dec' and integer for 'inc'/'dec'.")
			rule = {'groupname': self.currentgroup, 'rulename': self.currentrule}
			reason = element.attrib['reason'] if element.attrib.has_key('reason') else None
			return self.components.modify_attribute(name=element.attrib['name'],
			                                        value=value,
			                                        op=op,
			                                        rule=rule,
			                                        reason=reason)
		elif element.tag == TAG_SUPPRESS:
			assert(element[0].tag == TAG_EVENT_QUERY)
			query = self.parseRuleElement(element[0])
			rule = {'groupname': self.currentgroup, 'rulename': self.currentrule}
			reason = element.attrib['reason'] if element.attrib.has_key('reason') else None
			return self.components.suppress(rule, reason, query)
		elif element.tag == TAG_ASSOCIATE_WITH_CONTEXT:
			namefunc = self.parseMixedContent(element)
			return self.components.associate_with_context(self.currentgroup, namefunc)
		elif element.tag == TAG_ADD_REFERENCES:
			assert(element[0].tag == TAG_EVENT_QUERY)
			assert(element.attrib['type'] in EVENT_REFERENCE_TYPES)
			query = self.parseRuleElement(element[0])
			rule = {'groupname': self.currentgroup, 'rulename': self.currentrule}
			reason = element.attrib['reason'] if element.attrib.has_key('reason') else None
			return self.components.add_references(rule, reason, element.attrib['type'], query)
		elif element.tag == TAG_CREATE:
			assert(len(element)==1)
			assert(element[0].tag==TAG_EVENT)
			(inject, eventfunc) = self.parseRuleElement(element[0])
			return self.components.create(inject, eventfunc)
		elif element.tag == TAG_CREATE_CONTEXT:
			assert(len(element)==1 or len(element)==2)
			assert(element[0].tag == TAG_CONTEXT_NAME)
			namefunc = self.parseRuleElement(element[0])
			contextattribs = {}
			contextattribs['timeout'] = self.parseTime(element.attrib['timeout'])
			contextattribs['counter'] = self.parseInt(element.attrib['counter'])\
			                              if element.attrib.has_key('counter') else 0
			contextattribs['repeat'] = (element.attrib['repeat'] == "true")
			contextattribs['delay_associated'] = (element.attrib['delay_associated'] == "true")
			if len(element) == 2:
				eventtuple = self.parseRuleElement(element[1])
			else:
				eventtuple = None
			return self.components.create_context(self.currentgroup,
			                                      namefunc,
			                                      eventtuple,
			                                      contextattribs)
		elif element.tag == TAG_CONTEXT_NAME:
			return self.parseMixedContent(element)
		elif element.tag == TAG_DELETE_CONTEXT:
			namefunc = self.parseMixedContent(element)
			return self.components.delete_context(group = self.currentgroup, namefunc = namefunc)
		elif element.tag == TAG_MODIFY_CONTEXT:
			assert(element.attrib['counter_op'] in ['set', 'inc', 'dec'])
			namefunc = self.parseMixedContent(element)
			reset_timer = (element.attrib['reset_timer'] == "true")
			reset_associated_events = (element.attrib['reset_associated_events'] == "true")
			counter_op = element.attrib['counter_op']
			counter_value = self.parseInt(element.attrib['counter_value'])\
			                  if element.attrib.has_key('counter_value') else None
			return self.components.modify_context(self.currentgroup,
			                                      namefunc,
			                                      reset_timer,
			                                      reset_associated_events,
			                                      counter_op,
			                                      counter_value)
		elif element.tag == TAG_ACTION_PLUGIN:
			parameters = {}
			for child in element:
				parameters[child.attrib['name']] = self.parseRuleElement(child)
			return self.components.action_plugin(self.config,
			                                     self.logger,
			                                     element.attrib['name'],
			                                     parameters)
		elif element.tag == TAG_TRIGGER:
			field = element.attrib['field']
			return self.components.trigger(field)
		elif element.tag == TAG_EVENT_QUERY:
			assert(element.attrib['delay'] in ['true', 'false'])
			assert(element.attrib['time_source'] in ['creation', 'arrival'])
			name = element.attrib['name'] if element.attrib.has_key('name') else None
			self.currentquery = name
			if name != None:
				if not self.named_queries.has_key(self.currentgroup):
					self.named_queries[self.currentgroup] = {}
				if self.named_queries[self.currentgroup].has_key(name):
					self.parsingError("Duplicate query name: '%s'" % name)
			delay = element.attrib['delay'] == 'true'
			time_source = element.attrib['time_source']
			if element.attrib.has_key('max_age'):
				max_age = self.parseTime(element.attrib['max_age'])
			else:
				max_age = None
			# reference list for existence and loop checking
			if not self.query_references.has_key(self.currentgroup):
				self.query_references[self.currentgroup] = {}
			if not self.query_references[self.currentgroup].has_key(name):
				self.query_references[self.currentgroup][name] = set()
			# build the query determinator
			self.components = querycomponents
			query_operations = [self.parseRuleElement(child) for child in element]
			qdet = self.components.event_query(query_operations, max_age, time_source)
			self.components = rulecomponents
			if max_age == None: # max_age must be inferred
				# if the determinator is false independently of the event,
				# there is no need to cache or delay an event due to this query
				# ever; otherwise, we have a problem
				if qdet(predetermined_fields={'default': UNDEFINED}) != False:
					self.parsingError("max_age can't be inferred in query '%s'."
					                  % (name if name != None else "[unnamed query]"))
			else:
				self.query_determinators.append({
				  'max_age': max_age,
				  'determinator': qdet,
				  'delay': delay,
				  'time_source': time_source,
				  'rule': (self.currentgroup, self.currentrule),
				  'name': name if name != None else "[unnamed query]"
				})
			# build the actual query
			query_operations = [self.parseRuleElement(child) for child in element]
			query = self.components.event_query(query_operations, max_age, time_source)
			if name != None:
				self.named_queries[self.currentgroup][name] = (query, qdet)
			# return
			return query
		elif element.tag == TAG_INTERSECTION:
			queries = []
			for child in element:
				queries.append(self.parseRuleElement(child))
			return self.components.intersection(queries)
		elif element.tag == TAG_UNION:
			queries = []
			for child in element:
				queries.append(self.parseRuleElement(child))
			return self.components.union(queries)
		elif element.tag == TAG_COMPLEMENT:
			query = self.parseRuleElement(element[0])
			return self.components.complement(query)
		elif element.tag == TAG_FIRST_OF:
			sort_by = element.attrib['sort_by']
			assert(sort_by == "creation" or sort_by == "arrival")
			query = self.parseRuleElement(element[0])
			return self.components.first_of(sort_by, query)
		elif element.tag == TAG_LAST_OF:
			sort_by = element.attrib['sort_by']
			assert(sort_by == "creation" or sort_by == "arrival")
			query = self.parseRuleElement(element[0])
			return self.components.last_of(sort_by, query)
		elif element.tag == TAG_UNIQUE_BY:
			sort_by = element.attrib['sort_by']
			keep = element.attrib['keep']
			assert(sort_by == "creation" or sort_by == "arrival")
			assert(keep == "first" or keep == "last")
			query = self.parseRuleElement(element[0])
			field = element.attrib['field']
			if not ((field in EVENT_FIELDS) or field.startswith("attributes.")):
				self.parsingError("Unknown event field: %s" % field)
				return None
			return self.components.unique_by(field, sort_by, keep, query)
		elif element.tag == TAG_IS_TRIGGER:
			return self.components.is_trigger
		elif element.tag == TAG_IN_CONTEXT:
			namefunc = self.parseMixedContent(element)
			group = element.attrib['group'] if element.attrib.has_key('group') else self.currentgroup
			return self.components.in_context(group, namefunc)
		elif element.tag == TAG_MATCH_QUERY:
			name = element.text.strip()
			self.query_references[self.currentgroup][self.currentquery].add(name)
			return self.components.match_query(self.currentgroup, name)
		elif element.tag == TAG_EVENT_CLASS:
			return self.components.event_class(element.text.strip())
		elif element.tag == TAG_EVENT_NAME:
			return self.components.event_name(element.text.strip())
		elif element.tag == TAG_EVENT_TYPE:
			eventtype = element.text.strip()
			assert(eventtype in EVENT_TYPES)
			return self.components.event_type(eventtype)
		elif element.tag == TAG_EVENT_STATUS:
			status = element.text.strip()
			assert(status in EVENT_STATUSES)
			return self.components.event_status(status)
		elif element.tag == TAG_EVENT_HOST:
			namefunc = self.parseMixedContent(element)
			return self.components.event_host(namefunc)
		elif element.tag == TAG_EVENT_ATTRIBUTE:
			op = element.attrib['op']
			assert(op in ["eq", "ge", "le", "re"])
			valuefunc = self.parseMixedContent(element)
			if op == 're':
				if not element.attrib.has_key('regexp'):
					self.parsingError("event_attribute with op 're' needs"\
					                 +"additional attribute 'regexp'.")
					return None
				regexp = element.attrib['regexp']
			else:
				regexp = None
			try:
				return self.components.event_attribute(element.attrib['name'],
				                                       valuefunc,
				                                       op,
				                                       regexp=regexp)
			except re.error as e:
				self.parsingError("Error compiling regular expression in event_attribue: %s" % e)
				return None
		elif element.tag == TAG_EVENT_MIN_AGE:
			age = self.parseTime(element.text.strip())
			return self.components.event_min_age(age)
		elif element.tag == TAG_EVENT:
			inject = element.attrib['inject']
			assert(inject=="input" or inject=="output")
			eventdata = {'local': (element.attrib['local'] == "true"),
			             'status': element.attrib['status']}
			descriptionfunc = None
			attributefuncs = {}
			for child in element:
				if child.tag == TAG_NAME:
					eventdata['name'] = self.parseRuleElement(child)
				elif child.tag == TAG_DESCRIPTION:
					descriptionfunc = self.parseRuleElement(child)
				elif child.tag == TAG_ATTRIBUTE:
					(key, func) = self.parseRuleElement(child)
					attributefuncs[key] = func
				else:
					assert(False)
			return (inject, self.components.event(eventdata, descriptionfunc, attributefuncs))
		elif element.tag == TAG_NAME:
			return element.text.strip()
		elif element.tag == TAG_DESCRIPTION:
			return self.parseMixedContent(element)
		elif element.tag == TAG_ATTRIBUTE:
			return (element.attrib['name'], self.parseMixedContent(element))
		else:
			self.logger.logErr("Unhandled XML element: " + element.tag)
			assert(False) # untreated XML element - should never happen

# main - for testing only
if __name__ == '__main__':
	from ace.util import configuration, logging
	config = configuration.Config()
	logger = logging.Logger(config)
	rulemanager = RuleManager(config, logger)
