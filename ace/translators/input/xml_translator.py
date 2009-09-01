#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with XML event input translator.

Note that we can only use a SAX parser here, because we don't know, when new
events arrive.
"""

from xml.sax.handler import ContentHandler
from xml.sax import make_parser
from lxml import etree, sax

from ace.translators.input.base import InputTranslator
from ace.event import Event
from ace.util import constants

class EventGrabber(ContentHandler):
	"""
	Builds a tree from SAX events.
	"""

	def __init__(self, config, logger, parent):
		ContentHandler.__init__(self)
		self.config = config
		self.logger = logger
		self.parent = parent
		self.validator = etree.DTD(self.config.events_dtd)
		self.event_started = False
		self.events = []
		self.event_handler = None
	
	def __iter__(self):
		return self

	def next(self):
		"""
		Returns the next grabbed event, while there are any.
		"""
		if len(self.events)>0:
			return self.events.pop(0)
		else:
			raise StopIteration

	def startElement(self, tag, attrib):
		"""
		Called when an XML element starts.
		"""
		if tag == constants.EVENT_TAG_EVENT:
			self.event_handler = sax.ElementTreeContentHandler()
			self.event_handler.startDocument()
			self.event_started = True
		if self.event_started:
			# ugly, but necessary (incompatibilities between lxml and sax)
			attributes = {}
			if attrib.getLength()>0:
				for key in attrib.keys():
					attributes[(None, key)] = attrib[key]
			self.event_handler.startElement(tag, attributes)

	def endElement(self, tag):
		"""
		Called when an XML element stops.
		"""
		if tag == constants.EVENT_TAG_EVENT:
			if self.event_started:
				self.event_handler.endDocument()
				self.event_started = False
				root = self.event_handler.etree.getroot()
				if not self.validator.validate(root):
					self.parent.raiseException("XML validation not successful.")
				self.events.append(self.makeEvent(root))
				# self.event_handler.etree.getroot().clear()
		if self.event_started:
			self.event_handler.endElement(tag)

	def characters(self, data):
		"""
		Called when there are input characters.
		"""
		if self.event_started:
			self.event_handler.characters(data)

	def comment(self, text):
		"""
		Called when the parser encounters a comment.
		"""
		pass

	def makeEvent(self, root):
		"""
		Generates a new event from the parsed data.
		
		@param root: root entry of the event element tree
		"""
		kwargs = {}
		attributes = {}
		references = {}
		history = []
		for tag in root:
			if tag.tag in constants.EVENT_STRING_FIELDS:
				kwargs[tag.tag] = tag.text if tag.text != None else ""
			elif tag.tag == "creation" or tag.tag == "count":
				if not tag.text.isdigit():
					self.parent.raiseException("Content of '"+tag.tag+"' is not an integer.")
				else:
					kwargs[tag.tag] = int(tag.text)
			elif tag.tag == "attributes":
				for attribute in tag:
					attributes[attribute.attrib['key']] = attribute.text
			elif tag.tag == "references":
				for reference in tag:
					if not references.has_key(reference.attrib['type']):
						references[reference.attrib['type']] = []
					references[reference.attrib['type']].append(reference.text)
			elif tag.tag == "history":
				for entry in tag:
					historyentry = {}
					for part in entry:
						if part.tag in ['host', 'reason']:
							historyentry[part.tag] = part.text
						elif part.tag == "timestamp":
							if not part.text.isdigit():
								self.parent.logger.logWarn("XML input translator: History timestamp is"\
								                          +" not an integer: %s" % part.text)
								historyentry[part.tag] = 0
							else:
								historyentry[part.tag] = int(part.text)
						elif part.tag == "rule":
							historyentry[part.tag] = {"groupname": part[0].text, "rulename": part[1].text}
						elif part.tag == "reason":
							historyentry[part.tag] = []
							for reason in part:
								historyentry[part.tag].append(reason.text)
						elif part.tag == "fields":
							historyentry[part.tag] = []
							for field in part:
								historyentry[part.tag].append(field.text)
						else:
							assert(False)
					history.append(historyentry)
			else:
				assert(False)
		event = Event(**kwargs)
		if len(attributes)>0:
			event.attributes = attributes
		if len(references)>0:
			event.references = references
		if len(history)>0:
			event.history = history
		return event

class XMLTranslator(InputTranslator):
	"""
	Translates XML events into Event instances.
	"""

	def __init__(self, num, config, logger):
		InputTranslator.__init__(self, num, config, logger)
		self.grabber = EventGrabber(config, logger, self)
		self.parser = make_parser(["IncrementalParser"])
		self.parser.setContentHandler(self.grabber)

	def translate(self, inputdata):
		"""
		Translates new input data into an event.

		The input data does not have to represent exactly one event, but can
		start and end anywhere inside the event, as long as the complete stream
		is valid XML.
		"""
		self.parser.feed(inputdata)
		for event in self.grabber:
			yield event
