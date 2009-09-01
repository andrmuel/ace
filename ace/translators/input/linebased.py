#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Classes for translation of line based input.
"""

# stdlib
import re
import datetime
# other libs
from lxml import etree
# own code
from ace.translators.input.base import InputTranslator
from ace.event import Event

class TreeNode:
	"""
	Empty class to be (mis)used as a record.
	"""
	def __init__(self):
		self.text = None
		self.tail = None
		self.tag = None
		self.regexp = None
		self.attrib = None
		self.children = None

class LineBased(InputTranslator):
	"""
	Line based input translation.

	This class translates line based input data to events, according to the
	given rules.

	Options:
	 - rulefile: filename of xml file with translation rules
	"""

	TAG_ROOT = 'translation_linebased'
	TAG_MATCH = 'match'
	TAG_DESCRIPTION = 'description'
	TAG_HOST = 'host'
	TAG_ATTRIBUTE = 'attribute'
	TAG_DATETIME = 'datetime'
	TAG_MATCHGROUP = 'matchgroup'
	TAG_CREATE = 'create'
	TAG_DROP = 'drop'

	def __init__(self, num, config, logger):
		InputTranslator.__init__(self, num, config, logger)
		if not self.options.has_key('rulefile'):
			self.raiseException("Translator needs option 'rulefile'.")
		self.translation_tree = self.buildTree(self.parseRules(self.options['rulefile']))
		self.leftover = ""
		self.events = []

	def translate(self, inputdata):
		"""
		This is the main function, which processes the input.
		"""
		inputdata = self.leftover + inputdata
		lines = inputdata.split('\n')
		self.leftover = lines[-1]
		self.events = []
		for line in lines[:-1]:
			self.evaluateSubtree(self.translation_tree, line)
		for event in self.events:
			yield event

	def parseRules(self, rulefile):
		"""
		Parse the rules from the rule file - the lxml etree parser generates a
		tree with iterable nodes.
		
		@param rulefile: a filename of the XML file with translation rules, which must be valid according to the translation_linebased DTD
		"""
		parser = etree.XMLParser(attribute_defaults=True, dtd_validation=True,
		                         load_dtd=True, remove_comments=True)
		rules = etree.parse(rulefile, parser)
		root = rules.getroot()
		if root.tag != self.TAG_ROOT:
			self.raiseException("Unexpected XML rule root element: "+root.tag)
		return root

	def buildTree(self, element):
		"""
		Build a tree with translation information. The main reason for doing
		this (rather than directly using the lxml tree) is to precompile the
		regular expressions. Additinally, the generated tree is smaller than
		the original.
		
		@param element: an XML element containing a subtree
		"""
		node = TreeNode()
		# generic node content
		node.tag = element.tag
		node.attrib = element.attrib
		if element.text:
			node.text = element.text
		else:
			node.text = ''
		if element.tail:
			node.tail = element.tail
		else:
			node.tail = ''
		node.children = []
		# children
		for child in element:
			node.children.append(self.buildTree(child))
		# specific node content
		if element.tag == self.TAG_MATCH:
			node.regexp = re.compile(node.attrib['regexp'])
		return node

	def evaluateSubtree(self, node, line, event=None, match=None):
		"""
		For a given input line (or part thereof), this function evaluates the
		translation rule tree (or a subtree), and generates an event
		accordingly (or drops the line).
		
		@param node: a node of the translation rule tree
		@param line: the current input line
		@param event: a dictionary with the event information extracted so far
		@param match: a match object (the one from the enclosing match element)
		"""
		if node.tag == self.TAG_ROOT:
			for child in node.children:
				if self.evaluateSubtree(child, line, dict()):
					return True
		elif node.tag == self.TAG_MATCH:
			newmatch = node.regexp.search(line)
			if newmatch:
				for child in node.children:
					if child.tag == self.TAG_MATCH:
						if self.evaluateSubtree(child, line, event.copy(), newmatch):
							return True
					else:
						if self.evaluateSubtree(child, line, event, newmatch):
							return True
		elif node.tag == self.TAG_DESCRIPTION:
			event['description'] = node.text + reduce(lambda a, b: a + b,
			                                         [self.evaluateSubtree(child, line, match=match)
			                                           for child in node.children],
			                                         '')
		elif node.tag == self.TAG_HOST:
			event['host'] = node.text + reduce(lambda a, b: a + b,
			                                   [self.evaluateSubtree(child, line, match=match)
			                                     for child in node.children],
			                                   '')
		elif node.tag == self.TAG_ATTRIBUTE:
			if not event.has_key('attributes'):
				event['attributes'] = dict()
			event['attributes'][node.attrib['name']] = node.text +\
			                                           reduce(lambda a, b: a + b,
			                                                  [self.evaluateSubtree(child, line, match=match)
			                                                    for child in node.children],
			                                                  '')
		elif node.tag == self.TAG_DATETIME:
			timestr = node.text + reduce(lambda a, b: a + b,
			                             [self.evaluateSubtree(child, line, match=match)
			                               for child in node.children],
			                             '')
			creation = datetime.datetime.strptime(timestr.strip(), node.attrib['format'])
			if node.attrib['use_current_year']:
				creation = creation.replace(datetime.datetime.now().year)
			event['creation'] = creation.strftime("%s") # save as seconds since 1970
		elif node.tag == self.TAG_MATCHGROUP:
			try:
				if node.attrib['group'].isdigit():
					content = match.group(int(node.attrib['group']))
				else:
					content = match.group(node.attrib['group'])
				return content
			except IndexError:
				return ''
		elif node.tag == self.TAG_CREATE:
			event['name'] = node.text
			self.events.append(self.createEvent(event))
			return True
		elif node.tag == self.TAG_DROP:
			return True
		else: # this is definitely a code error -> escalate
			raise Exception, "Internal error: Unknown XML element."
		return False

	def createEvent(self, event):
		"""
		Create an event and insert it into the queue.
		
		@param event: a dictionary with event information
		"""
		if not event.has_key('host'):
			event['host'] = self.config.hostname
		return Event(**event)

