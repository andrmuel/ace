#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Module with XML output translator.
"""

from lxml import etree
from lxml.builder import E
from ace.util import constants
from ace.translators.output.base import OutputTranslator

class XMLTranslator(OutputTranslator):
	"""
	Class to translate events into XML data.
	"""

	def __init__(self, num, config, logger):
		OutputTranslator.__init__(self, num, config, logger)
		self.first = True

	def translate(self, event):
		"""
		Translates an event into its XML representation.
		"""
		# mandatory data
		root = E.event(
		         E.name(event.getName()),
		         E.description(event.getDescription()),
		         E.id(event.getID()),
		         E.type(event.getType()),
		         E.status(event.getStatus()),
		         E.count(str(event.getCount())),
		         E.host(event.getHost()),
		         E.creation(str(event.getCreationTime()))
		       )
		# attributes
		attr = event.getAttributes()
		if len(attr)>0:
			attributes = E.attributes()
			for key in attr:
				attributes.append(E.attribute({"key":key}, attr[key]))
			root.append(attributes)
		# references
		refs = event.getAllReferences()
		if len(refs) > 0:
			references = E.references()
			for key in refs:
				for reference in refs[key]:
					references.append(E.reference({"type":key}, reference))
			root.append(references)
		# history
		hist = event.getHistory()
		if len(hist)>0:
			history = E.history()
			for entry in hist:
				historyentry = E.historyentry(
				                 E.rule(
				                   E.groupname(entry['rule']['groupname']),
				                   E.rulename(entry['rule']['rulename'])
				                 ),
				                 E.host(entry['host']),
				                 E.timestamp(str(entry['timestamp']))
				               )
				if entry.has_key("fields"):
					fields = E.fields()
					for field in entry['fields']:
						fields.append(E.field(field))
					historyentry.append(fields)
				if entry.has_key("reason"):
					if type(entry['reason']) == str:
						historyentry.append(E.reason(entry['reason']))
				history.append(historyentry)
			root.append(history)
		# check validity
		validator = etree.DTD(self.config.events_dtd)
		if not validator.validate(root): # only a subtree - but it still validates correctly
			self.raiseException("XML validation of generated content not successful.")
		# return XML string
		return etree.tostring(root, pretty_print=True)

	def getHeader(self):
		return constants.EVENT_TAG_EVENTS_START+"\n"

	def getFooter(self):
		return constants.EVENT_TAG_EVENTS_END+"\n"
