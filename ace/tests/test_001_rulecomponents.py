#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

import unittest
import re
import types
import sys
from operator import xor
from ace.basisfunctions import rulecomponents
from ace.util import configuration, logging
from ace.util.exceptions import *
from ace import event, contexts, cache, ticker, rulebase
from ace.plugins import condition as condition_plugins

class TestCache:
	def __init__(self, events):
		self.events = events
	def getEvents(self):
		return self.events

class TestRuleManager(rulebase.RuleManager):
	def __init__(self, classes={}, queries=None):
		self.classtable = classes
		self.named_queries = queries

class TestRuleComponents(unittest.TestCase):
	"""
	Unittest for the rulecomponents module.
	"""
	
	def setUp(self):
		self.config = configuration.Config()
		self.logger = logging.Logger(self.config)
		self.ticker = ticker.Ticker(self.config, self.logger)

	def test_ifthenelse(self):
		even = lambda **kwargs: kwargs['x']%2 == 0 # a function, which always returns true
		append2 = lambda **kwargs: kwargs['a'].append(2)
		append3 = lambda **kwargs: kwargs['a'].append(3)
		append4 = lambda **kwargs: kwargs['a'].append(4)
		ifthenelse = rulecomponents.if_then_else(even, [append2, append3], [append4])
		a = []
		ifthenelse(x=0, a=a) # even, thus 2 and 3 should be appended
		ifthenelse(x=1, a=a) # odd, thus 3 shoud be appended
		self.assert_(a==[2,3,4])
	
	def test_and(self):
		larger5 = lambda x: x>5
		even = lambda x: x%2==0
		smaller10 = lambda x: x<10
		# no function > should always be true
		alwaystrue = rulecomponents.and_([])
		self.assert_(alwaystrue(x=42)==True)
		# one function > should be unchanged
		still_even = rulecomponents.and_([even])
		result = [i for i in range(10) if still_even(x=i)]
		self.assert_(result==[0,2,4,6,8])
		# combination of 3 functions
		even_and_larger5_and_smaller10 = rulecomponents.and_([even,larger5,smaller10])
		result = [i for i in range(100) if even_and_larger5_and_smaller10(x=i)]
		self.assert_(result==[6,8])

	def test_or(self):
		smaller5 = lambda x: x<5
		even = lambda x: x%2==0
		larger10 = lambda x: x>10
		# no function > should always be true
		alwaystrue = rulecomponents.or_([])
		self.assert_(alwaystrue(x=42)==True)
		# one function > should be unchanged
		still_even = rulecomponents.or_([even])
		result = [i for i in range(10) if still_even(x=i)]
		self.assert_(result==[0,2,4,6,8])
		# combination of 3 functions
		even_and_larger5_and_smaller10 = rulecomponents.or_([even,smaller5,larger10])
		result = [i for i in range(13) if even_and_larger5_and_smaller10(x=i)]
		self.assert_(result==[0,1,2,3,4,6,8,10,11,12]) # all values <5, even or >10

	def test_not(self):
		is_even = lambda x: x%2 == 0
		is_odd = rulecomponents.not_(is_even)
		for i in range(10):
			self.assert_(xor(is_even(x=i), is_odd(x=i)))

	def test_context(self):
		t1 = rulecomponents.context("test_group_nonexistant", lambda **kwargs: "foo")
		t2 = rulecomponents.context("test_group", lambda **kwargs: "test_name")
		t3 = rulecomponents.context("test_group", lambda **kwargs: "test_name2")
		t4 = rulecomponents.context("test_group", lambda **kwargs: "test_name2", counter_val=3, op="eq")
		t5 = rulecomponents.context("test_group", lambda **kwargs: "test_name2", counter_val=4, op="eq")
		t6 = rulecomponents.context("test_group", lambda **kwargs: "test_name2", counter_val=4, op="le")
		t7 = rulecomponents.context("test_group", lambda **kwargs: "test_name2", counter_val=2, op="ge")
		t8 = rulecomponents.context("test_group", lambda **kwargs: "test_name2", counter_val=3, op="ge")
		t9 = rulecomponents.context("test_group", lambda **kwargs: "test_name2", counter_val=4, op="ge")
		cm = contexts.ContextManager(self.config, self.logger, self.ticker, None)
		cm.createContext("test_group", "test_name", None, None, {'timeout': 0})
		cm.createContext("test_group", "test_name2", None, None, {'timeout':0, 'counter':3})
		self.assert_(t1(contexts=cm)==False)
		self.assert_(t2(contexts=cm)==True)
		self.assert_(t3(contexts=cm)==True)
		self.assert_(t4(contexts=cm)==True)
		self.assert_(t5(contexts=cm)==False)
		self.assert_(t6(contexts=cm)==True)
		self.assert_(t7(contexts=cm)==True)
		self.assert_(t8(contexts=cm)==True)
		self.assert_(t9(contexts=cm)==False)

	def test_trigger_match(self):
		g = event.EventGenerator()
		e = g.randomEvent()
		e.host = "FOO"
		e.name = "BAR"
		host_is_foo = rulecomponents.event_host(lambda **kwargs: "FOO")
		name_is_bar = rulecomponents.event_name("BAR")
		both = rulecomponents.trigger_match([host_is_foo, name_is_bar])
		none = rulecomponents.trigger_match([])
		self.assert_(both(trigger=e)==True)
		self.assert_(none(trigger=e)==True)
		e.name = "FOO"
		self.assert_(both(trigger=e)==False)

	def test_count(self):
		g = event.EventGenerator()
		events = g.randomEvents(20)
		for i in range(10):
			events[i].host = 'test'
		event_query = lambda **kwargs: [x for x in kwargs['events'] if x.host=='test']
		eq10 = rulecomponents.count(10, op="eq", query=event_query)
		eq11 = rulecomponents.count(11, op="eq", query=event_query)
		ge9 = rulecomponents.count(9, op="ge", query=event_query)
		ge10 = rulecomponents.count(10, op="ge", query=event_query)
		ge11 = rulecomponents.count(11, op="ge", query=event_query)
		le9 = rulecomponents.count(9, op="le", query=event_query)
		le10 = rulecomponents.count(10, op="le", query=event_query)
		le11 = rulecomponents.count(11, op="le", query=event_query)
		self.assertTrue(eq10(events=events))
		self.assertFalse(eq11(events=events))
		self.assertTrue(ge9(events=events))
		self.assertTrue(ge10(events=events))
		self.assertFalse(ge11(events=events))
		self.assertFalse(le9(events=events))
		self.assertTrue(le10(events=events))
		self.assertTrue(le11(events=events))

	def test_sequence(self):
		cache = TestCache([
			event.Event(name="TEST", host="A", creation=1, arrival=1),
			event.Event(name="TEST", host="B", creation=2, arrival=1),
			event.Event(name="TEST", host="B", creation=3, arrival=1),
			event.Event(name="TEST", host="C", creation=2, arrival=2),
			event.Event(name="TEST", host="C", creation=3, arrival=2),
		])
		hosta = rulecomponents.event_host(lambda **kwargs: "A")
		hostb = rulecomponents.event_host(lambda **kwargs: "B")
		hostc = rulecomponents.event_host(lambda **kwargs: "C")
		seq_empty_any = rulecomponents.sequence("creation", "any", [])
		seq_empty_all = rulecomponents.sequence("creation", "all", [])
		seq_empty_any_arrival = rulecomponents.sequence("arrival", "any", [])
		seq_ab_any = rulecomponents.sequence("creation", "any", [hosta, hostb])
		seq_ab_all = rulecomponents.sequence("creation", "all", [hosta, hostb])
		seq_abc_any = rulecomponents.sequence("creation", "any", [hosta, hostb, hostc])
		seq_abc_all = rulecomponents.sequence("creation", "all", [hosta, hostb, hostc])
		seq_bc_any = rulecomponents.sequence("creation", "any", [hostb, hostc])
		seq_bc_all = rulecomponents.sequence("creation", "all", [hostb, hostc])
		seq_ab_any_arrival = rulecomponents.sequence("arrival", "any", [hosta, hostb])
		seq_ab_all_arrival = rulecomponents.sequence("arrival", "all", [hosta, hostb])
		seq_bc_any_arrival = rulecomponents.sequence("arrival", "any", [hostb, hostc])
		seq_bc_all_arrival = rulecomponents.sequence("arrival", "all", [hostb, hostc])
		self.assert_(seq_empty_any(query_events=cache.getEvents())==True)
		self.assert_(seq_empty_all(query_events=cache.getEvents())==True)
		self.assert_(seq_empty_any_arrival(query_events=cache)==True)
		self.assert_(seq_ab_any(query_events=cache.getEvents())==True)
		self.assert_(seq_ab_all(query_events=cache.getEvents())==True)
		self.assert_(seq_abc_any(query_events=cache.getEvents())==True)
		self.assert_(seq_abc_all(query_events=cache.getEvents())==False)
		self.assert_(seq_bc_any(query_events=cache.getEvents())==True)
		self.assert_(seq_bc_all(query_events=cache.getEvents())==False)
		self.assert_(seq_ab_any_arrival(query_events=cache.getEvents())==False)
		self.assert_(seq_ab_all_arrival(query_events=cache.getEvents())==False)
		self.assert_(seq_bc_any_arrival(query_events=cache.getEvents())==True)
		self.assert_(seq_bc_all_arrival(query_events=cache.getEvents())==True)

	def test_pattern(self):
		alphabet = lambda **kwargs: kwargs['string']
		pattern = rulecomponents.pattern(alphabet, re.compile("foo"))
		self.assert_(pattern(string="_foobar_")==True)
		self.assert_(pattern(string="_bar_")==False)

	def test_alphabet(self):
		cache = TestCache([
			event.Event(name="A", host="A", creation=1, arrival=6),
			event.Event(name="B", host="A", creation=2, arrival=5),
			event.Event(name="B", host="A", creation=3, arrival=4),
			event.Event(name="B", host="C", creation=4, arrival=3),
			event.Event(name="C", host="C", creation=5, arrival=2),
			event.Event(name="C", host="E", creation=5, arrival=2), # note the timestamps -> sorting must be stable
		])
		nameA = rulecomponents.event_query([rulecomponents.event_name("A")], None, None)
		nameBhostA = rulecomponents.event_query([rulecomponents.event_name("B"), rulecomponents.event_host(lambda **kwargs: "A")], None, None)
		nameB = rulecomponents.event_query([rulecomponents.event_name("B")], None, None)
		nameChostC = rulecomponents.event_query([rulecomponents.event_name("C"), rulecomponents.event_host(lambda **kwargs: "C")], None, None)
		nameC = rulecomponents.event_query([rulecomponents.event_name("C")], None, None)
		alphabet = rulecomponents.alphabet(sort_by="creation", symbols=[('f', nameA), ('o', nameBhostA), ('b', nameB), ('a', nameChostC), ('r', nameC)])
		alphabet2 = rulecomponents.alphabet(sort_by="arrival", symbols=[('f', nameA), ('o', nameBhostA), ('b', nameB), ('a', nameChostC), ('r', nameC)])
		self.assert_(alphabet(cache=cache)=="foobar")
		self.assert_(alphabet2(cache=cache)=="arboof") # not raboof, because the sorting of the two events with the same timestamp is not changed (see above)

	def test_symbol(self):
		# can't really test much here ...
		symbol = rulecomponents.symbol('a', lambda x: 2*x)
		self.assert_(len(symbol)==2)
		self.assert_(symbol[0]=='a')
		self.assert_(symbol[1](2)==4)
		

	def test_regexp(self):
		# can't really test much here ...
		self.assert_(rulecomponents.regexp("(foo)*")==re.compile("(foo)*"))

	def test_within(self):
		# query-generator: generates a query, which generates events with the given timestamps
		query = lambda timestamps: lambda **kwargs: [event.Event(name="TEST:EVENT", host="host-00", creation=t, arrival=t) for t in timestamps]
		q0 = query([])
		q1 = query([0,1,10])
		q2 = query([1,10,20])
		q3 = query([15])
		q4 = query([50])
		q5 = query([51])

		# no queries -> true (should not happen according to DTD)
		self.assert_(rulecomponents.within(timeframe=100, timeref="creation", match="all", event_queries=[])()==True)
		self.assert_(rulecomponents.within(timeframe=100, timeref="arrival", match="any", event_queries=[])()==True)
		# empty query must yield false
		self.assert_(rulecomponents.within(timeframe=100, timeref="arrival", match="all", event_queries=[q0,q1])()==False)
		self.assert_(rulecomponents.within(timeframe=100, timeref="creation", match="any", event_queries=[q0,q1])()==False)
		# all and any should be within 20 for q1/q2/q3:
		self.assert_(rulecomponents.within(timeframe=20, timeref="creation", match="all", event_queries=[q1,q2,q3])()==True)
		self.assert_(rulecomponents.within(timeframe=20, timeref="creation", match="any", event_queries=[q1,q2,q3])()==True)
		# but only any within 19, not all
		self.assert_(rulecomponents.within(timeframe=19, timeref="creation", match="all", event_queries=[q1,q2,q3])()==False)
		self.assert_(rulecomponents.within(timeframe=19, timeref="creation", match="any", event_queries=[q1,q2,q3])()==True)
		# any within 5,
		self.assert_(rulecomponents.within(timeframe=5, timeref="creation", match="any", event_queries=[q1,q2,q3])()==True)
		# q4 is within a window of 0
		self.assert_(rulecomponents.within(timeframe=0, timeref="creation", match="all", event_queries=[q4])()==True)
		self.assert_(rulecomponents.within(timeframe=0, timeref="creation", match="any", event_queries=[q4])()==True)
		# q4/q5 aren't within 0
		self.assert_(rulecomponents.within(timeframe=0, timeref="creation", match="all", event_queries=[q4,q5])()==False)
		self.assert_(rulecomponents.within(timeframe=0, timeref="creation", match="any", event_queries=[q4,q5])()==False)
		# but within one
		self.assert_(rulecomponents.within(timeframe=1, timeref="creation", match="all", event_queries=[q4,q5])()==True)
		self.assert_(rulecomponents.within(timeframe=1, timeref="creation", match="any", event_queries=[q4,q5])()==True)
		
		
	def test_within_any(self):
		# evetns, tmin, tmax, timeframe
		self.assert_(rulecomponents.within_any([[1],[2]],0)==False)
		self.assert_(rulecomponents.within_any([[1],[2,3]],1)==True)
		self.assert_(rulecomponents.within_any([[1],[1,2]],0)==True)
		self.assert_(rulecomponents.within_any([range(10),range(20)],0)==True)
		self.assert_(rulecomponents.within_any([[4],[10],[5],[-10,-20]],20)==True)
		self.assert_(rulecomponents.within_any([[4],[10],[5],[-10,-20]],19)==False)
		# this isn't really time-consuming -> minmax and maxmin are far apart:
		self.assert_(rulecomponents.within_any([range(1000*i,1000*(i+1)) for i in range(1000)],998001)==True) # minmax: 999, maxmin: 999000 -> d: 998001 
		self.assert_(rulecomponents.within_any([range(1000*i,1000*(i+1)) for i in range(1000)],998000)==False)
		# this should be worse:
		# (2 tests, each 1000 * 1000 timestamps; takes about 7 seconds)
		#self.assert_(rulecomponents.within_any([range(i,i+10000,1000) for i in range(1000)], 999)==True)
		#self.assert_(rulecomponents.within_any([range(i,i+10000,1000) for i in range(1000)], 998)==False)

	def test_condition_plugin(self):
		# note: there is a special test suite for each plugin, thus, some short checks should be enough here
		self.wday = rulecomponents.condition_plugin(None, None, "weekday", parameters={'days': '0'}, queries=[])
		self.assert_(type(self.wday)==types.FunctionType)
		self.assertRaises(PluginNotFoundException, condition_plugins.get_plugin, "foobar")
		self.assertRaises(PluginException, rulecomponents.condition_plugin, None, None, name="weekday", parameters={'day': '0'}, queries=[]) # no param days
		self.assertRaises(PluginException, rulecomponents.condition_plugin, None, None, name="weekday", parameters={'days': '0'}, queries=[0]) # too many queries
		self.assertRaises(PluginException, rulecomponents.condition_plugin, None, None, name="weekday", parameters={'days': 'x'}, queries=[]) # day x can't be parsed
	
	# drop: see cache tests

	# forward: see cache tests

	# compress: see cache tests

	def test_trigger(self):
		e = event.Event(name="FOO", host="BAR")
		e.setAttribute('A',3,'set')
		name = rulecomponents.trigger(field="name")
		host = rulecomponents.trigger(field="host")
		xy  = rulecomponents.trigger(field="xy")
		attrA = rulecomponents.trigger(field="attributes.A")
		attrB = rulecomponents.trigger(field="attributes.B")
		self.assert_(name(trigger=e)=="FOO")
		self.assert_(host(trigger=e)=="BAR")
		self.assert_(xy(trigger=e)=="")
		self.assert_(attrA(trigger=e)=="3")
		self.assert_(attrB(trigger=e)=="")

	def test_intersection(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(15):
			events[i].host = "FOO"
		for i in range(5,20):
			events[i].name = "BAR"
		host_is_foo = rulecomponents.event_host(lambda **kwargs: "FOO")
		name_is_bar = rulecomponents.event_name("BAR")
		both = rulecomponents.intersection([host_is_foo, name_is_bar])
		all = rulecomponents.intersection([])
		self.assert_(len(both(query_events=events))==10)
		self.assert_(sorted(both(query_events=events))==sorted(events[5:15]))
		self.assert_(len(all(query_events=events))==100)

	def test_union(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(15):
			events[i].host = "FOO"
		for i in range(5,20):
			events[i].name = "BAR"
		host_is_foo = rulecomponents.event_host(lambda **kwargs: "FOO")
		name_is_bar = rulecomponents.event_name("BAR")
		both = rulecomponents.union([host_is_foo, name_is_bar])
		all = rulecomponents.union([])
		self.assert_(len(both(query_events=events))==20)
		self.assert_(sorted(both(query_events=events))==sorted(events[0:20]))
		self.assert_(len(all(query_events=events))==100)

	def test_complement(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		cache = TestCache(events)
		for i in range(15):
			events[i].host = "FOO"
		host_is_foo = rulecomponents.event_host(lambda **kwargs: "FOO")
		complement = rulecomponents.complement(host_is_foo)
		self.assert_(len(complement(cache=cache, query_events=events))==85)
		self.assert_(sorted(complement(cache=cache, query_events=events))==sorted(events[15:100]))

	def test_first_of(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		cache = TestCache(events)
		events[42].creation -= 10
		events[43].arrival -= 10
		first_of_creation = rulecomponents.first_of("creation", lambda **kwargs: kwargs['query_events'])
		first_of_arrival = rulecomponents.first_of("arrival", lambda **kwargs: kwargs['query_events'])
		creation_first = first_of_creation(query_events = events)
		arrival_first = first_of_arrival(query_events = events)
		self.assert_(creation_first == [events[42]])
		self.assert_(arrival_first == [events[43]])

	def test_last_of(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[42].creation += 100
		events[43].arrival += 100
		last_of_creation = rulecomponents.last_of("creation", lambda **kwargs: kwargs['query_events'])
		last_of_arrival = rulecomponents.last_of("arrival", lambda **kwargs: kwargs['query_events'])
		creation_last = last_of_creation(query_events = events)
		arrival_last = last_of_arrival(query_events = events)
		self.assert_(creation_last == [events[42]])
		self.assert_(arrival_last == [events[43]])

	def test_unique_by(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for e in events:
			e.host = "TEST"
		events[42].creation -= 100
		events[42].host = "FOO"
		events[43].creation += 100
		events[43].host = "FOO"
		events[44].arrival -= 100
		events[44].host = "FOO"
		events[45].arrival += 100
		events[45].host = "FOO"
		unique_by_creation_first = rulecomponents.unique_by("host", "creation", "first", lambda **kwargs: kwargs['query_events'])
		unique_by_creation_last = rulecomponents.unique_by("host", "creation", "last", lambda **kwargs: kwargs['query_events'])
		unique_by_arrival_first = rulecomponents.unique_by("host", "arrival", "first", lambda **kwargs: kwargs['query_events'])
		unique_by_arrival_last = rulecomponents.unique_by("host", "arrival", "last", lambda **kwargs: kwargs['query_events'])
		events_unique_creation_first = unique_by_creation_first(query_events = events)
		events_unique_creation_last = unique_by_creation_last(query_events = events)
		events_unique_arrival_first = unique_by_arrival_first(query_events = events)
		events_unique_arrival_last = unique_by_arrival_last(query_events = events)
		# number of selected events
		self.assert_(len(events_unique_creation_first) == 2)
		self.assert_(len(events_unique_creation_last) == 2)
		self.assert_(len(events_unique_arrival_first) == 2)
		self.assert_(len(events_unique_arrival_last) == 2)
		# event with host FOO
		fooevent = lambda evts: [e for e in evts if e.host=="FOO"][0]
		self.assert_(fooevent(events_unique_creation_first) == events[42])
		self.assert_(fooevent(events_unique_creation_last) == events[43])
		self.assert_(fooevent(events_unique_arrival_first) == events[44])
		self.assert_(fooevent(events_unique_arrival_last) == events[45])
		# empty list
		empty = unique_by_creation_first(query_events = [])
		self.assert_(len(empty) == 0)

	def test_unique_by_attribute(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[42].setAttribute("foo", "bar")
		events[42].creation -= 100
		events[43].setAttribute("foo", "bar")
		events[44].setAttribute("foo", "bar")
		events[45].setAttribute("foo", "baz")
		unique_by_attribute_foo = rulecomponents.unique_by("attributes.foo", "creation", "first", lambda **kwargs: kwargs['query_events'])
		unique_events = unique_by_attribute_foo(query_events = events)
		# event with host FOO
		self.assert_(len(unique_events) == 3)  # "bar", "baz" and ""
		barevent = lambda evts: [e for e in evts if e.getAttribute("foo")=="bar"][0]
		self.assert_(barevent(unique_events) == events[42])

	def test_is_trigger(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		is_trigger = rulecomponents.is_trigger
		trigger = is_trigger(query_events = events, trigger = events[42])
		no_trigger = is_trigger(query_events = events, trigger = g.randomEvent())
		self.assert_(len(trigger)==1)
		self.assert_(trigger[0] == events[42])
		self.assert_(len(no_trigger) == 0)

	def test_in_context(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[42].addDelayContext("foo", "a")
		events[43].addCacheContext("foo", "a")
		events[44].addCacheContext("foo", "b")
		events[45].addDelayContext("bar", "a")
		in_ctx = rulecomponents.in_context("foo", lambda **kwargs: "a")
		evnts = in_ctx(query_events = events)
		self.assert_(len(evnts) == 2)
		self.assert_(evnts[0] == events[42])
		self.assert_(evnts[1] == events[43])
	
	def test_match_query(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[42].host = "FOO"
		cache = TestCache(events)
		query = rulecomponents.event_query([rulecomponents.event_host(lambda **kwargs: "FOO")], None, "creation")
		queries = {"foo": {"bar": [query]}}
		rulemanager = TestRuleManager(queries = queries)
		match_query = rulecomponents.match_query("foo", "bar")
		evts = match_query(cache=cache, query_events=[], rulemanager=rulemanager)
		self.assert_(len(evts)==1)
		self.assert_(evts[0]==events[42])

	def test_event_class(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[42].name = "FOO"
		events[43].name = "BAR"
		classes = {"FOO": set(["bar", "baz"]), "BAR": set(["bar"])}
		rulemanager = TestRuleManager(classes = classes)
		event_class = rulecomponents.event_class("baz")
		evts = event_class(query_events=events, rulemanager=rulemanager)
		self.assert_(len(evts)==1)
		self.assert_(evts[0]==events[42])

	def test_event_name(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(15):
			events[i].name = "FOO"
		name_is_FOO = rulecomponents.event_name("FOO")
		self.assert_(len(name_is_FOO(query_events=events))==15)

	def test_event_type(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(100):
			if i < 15:
				events[i].type = "raw"
			else:
				events[i].type = "compressed"
		type_is_raw = rulecomponents.event_type("raw")
		self.assert_(len(type_is_raw(query_events=events))==15)

	def test_event_status(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(100):
			if i < 15:
				events[i].status = "active"
			else:
				events[i].status = "inactive"
		status_is_active = rulecomponents.event_status("active")
		self.assert_(len(status_is_active(query_events=events))==15)
		
	def test_event_host(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(15):
			events[i].host = "FOO"
		host_is_foo = rulecomponents.event_host(lambda **kwargs: "FOO")
		self.assert_(len(host_is_foo(query_events=events))==15)
		
	def test_event_attribute(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		for i in range(15):
			events[i].setAttribute("foo", "bar")
		attr_foo_is_bar = rulecomponents.event_attribute("foo", lambda **kwargs: "bar", "eq")
		self.assert_(len(attr_foo_is_bar(query_events=events))==15)
		for i in range(10, 20):
			events[i].setAttribute("foo", str(i))
		attr_foo_is_ge15 = rulecomponents.event_attribute("foo", lambda **kwargs: "15", "ge")
		attr_foo_is_le10 = rulecomponents.event_attribute("foo", lambda **kwargs: "10", "le")
		self.assert_(len(attr_foo_is_ge15(query_events=events))==5)
		self.assert_(attr_foo_is_le10(query_events=events)[0] == events[10])

	def test_event_attribute_regexp(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[10].setAttribute("foo", "bar")
		events[11].setAttribute("foo", "baar")
		events[12].setAttribute("foo", "bahr")
		attr_foo_matches_bar = rulecomponents.event_attribute("foo", None, "re", "^baa?r$")
		self.assert_(len(attr_foo_matches_bar(query_events=events))==2)
		self.assert_(attr_foo_matches_bar(query_events=events)[1] == events[11])

	def test_event_min_age(self):
		g = event.EventGenerator()
		events = g.randomEvents(100)
		events[10].creation -= 200
		events[11].creation -= 200
		min_age = rulecomponents.event_min_age(100)
		self.assert_(len(min_age(query_events=events))==2)

	def test_mixed_content(self):
		f = rulecomponents.mixed_content('foo', [lambda **kwargs: 'bar', lambda **kwargs: 'baz'])
		self.assert_(f(x=42)=='foobarbaz')

if __name__ == '__main__':
	unittest.main()

