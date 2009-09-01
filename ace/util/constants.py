#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Internal constants.
"""


# global debug switch
DEBUG = True

# undefined boolean state
UNDEFINED = -1 # should not be a string, True or False
DEFINED = -2 # should not be a string, True or False

# event properties
EVENT_FIELDS = ['name', 'description', 'id', 'type', 'status', 'count', 'host',
                'creation', 'attributes', 'references', 'history', 'arrival', 'local']
EVENT_STRING_FIELDS =  ['name', 'description', 'id', 'type', 'status', 'host', 'local']
EVENT_TYPES = ['raw', 'compressed', 'aggregated', 'synthetic', 'timeout', 'internal']
EVENT_TYPES_ANY = ['any']+EVENT_TYPES
EVENT_STATUSES = ['active', 'inactive']
EVENT_REFERENCE_TYPES = ['child', 'parent', 'cross']

EVENT_TAG_EVENTS = "events"
EVENT_TAG_EVENTS_START = "<events>"
EVENT_TAG_EVENTS_END = "</events>"
EVENT_TAG_EVENT = "event"

# XML rule tags
TAG_ROOT = 'rules'
TAG_GROUP = 'group'
TAG_RULE = 'rule'
TAG_EVENTS = 'events'
TAG_CONDITIONS = 'conditions'
TAG_ACTIONS = 'actions'
TAG_ALTERNATIVE_ACTIONS = 'alternative_actions'
TAG_WHEN_ANY = 'when_any'
TAG_WHEN_CLASS = 'when_class'
TAG_WHEN_EVENT = 'when_event'
TAG_AND = 'and'
TAG_OR = 'or'
TAG_NOT = 'not'
TAG_CONTEXT = 'context'
TAG_TRIGGER_MATCH = 'trigger_match'
TAG_COUNT = 'count'
TAG_SEQUENCE = 'sequence'
TAG_PATTERN = 'pattern'
TAG_ALPHABET = 'alphabet'
TAG_SYMBOL = 'symbol'
TAG_REGEXP = 'regexp'
TAG_WITHIN = 'within'
TAG_CONDITION_PLUGIN = 'condition_plugin'
TAG_ACTION_PLUGIN = 'action_plugin'
TAG_PLUGIN_PARAMETER = 'plugin_parameter'
TAG_SUBBLOCK = 'subblock'
TAG_SELECT_EVENTS = 'select_events'
TAG_DROP = 'drop'
TAG_FORWARD = 'forward'
TAG_COMPRESS = 'compress'
TAG_AGGREGATE = 'aggregate'
TAG_MODIFY = 'modify'
TAG_MODIFY_ATTRIBUTE = 'modify_attribute'
TAG_SUPPRESS = 'suppress'
TAG_ASSOCIATE_WITH_CONTEXT = 'associate_with_context'
TAG_ADD_REFERENCES = 'add_references'
TAG_CREATE = 'create'
TAG_CREATE_CONTEXT = 'create_context'
TAG_CONTEXT_NAME = 'context_name'
TAG_DELETE_CONTEXT = 'delete_context'
TAG_MODIFY_CONTEXT = 'modify_context'
TAG_ACTION_PLUGIN = 'action_plugin'
TAG_TRIGGER = 'trigger'
TAG_EVENT_QUERY = 'event_query'
TAG_INTERSECTION = 'intersection'
TAG_UNION = 'union'
TAG_COMPLEMENT = 'complement'
TAG_FIRST_OF = 'first_of'
TAG_LAST_OF = 'last_of'
TAG_UNIQUE_BY = 'unique_by'
TAG_IS_TRIGGER = 'is_trigger'
TAG_IN_CONTEXT = 'in_context'
TAG_MATCH_QUERY = 'match_query'
TAG_EVENT_CLASS = 'event_class'
TAG_EVENT_NAME = 'event_name'
TAG_EVENT_TYPE = 'event_type'
TAG_EVENT_STATUS = 'event_status'
TAG_EVENT_HOST = 'event_host'
TAG_EVENT_ATTRIBUTE = 'event_attribute'
TAG_EVENT_MIN_AGE = 'event_min_age'
TAG_EVENT = 'event'
TAG_NAME = 'name'
TAG_DESCRIPTION = 'description'
TAG_ATTRIBUTE = 'attribute'

# class list
CLASSLIST_ROOT = 'eventclasses'
