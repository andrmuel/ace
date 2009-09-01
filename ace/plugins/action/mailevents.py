#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Mail action plugin module.
"""

import smtplib
from email import Message
import socket
from ace.plugins.action.base import ActionPlugin

class MailAction(ActionPlugin):
	"""
	Simple MailAction class - provides a plugin to send events in a mail.

	Parameters:
	 - from: sender address
	 - to: receiver address
	 - subject: mail subject
	 - text: mail body
	"""
	def __init__(self, config, logger, parameters):
		ActionPlugin.__init__(self, config, logger, parameters)
		if not parameters.has_key("subject"):
			self.raiseException("MailAction", "Plugin needs parameter 'subject'.")
		if not parameters.has_key("text"):
			self.raiseException("MailAction", "Plugin needs parameter 'text'.")
		if not parameters.has_key("to"):
			self.raiseException("MailAction", "Plugin needs parameter 'to'.")
		if not parameters.has_key("from"):
			self.raiseException("MailAction", "Plugin needs parameter 'from'.")
		self.to = parameters['to']
		self.from_ = parameters['from']
		self.text = parameters['text']
		self.subject = parameters['subject']

	def executeAction(self, events):
		"""
		Sends an email with the given events.
		"""
		msg = Message.Message()
		msg['From'] = self.from_
		msg['To'] = self.to
		msg['Subject'] = self.subject
		text = self.text+'\n'
		for event in events:
			text += str(event)+'\n'
		msg.set_payload(text)
		try:
			server = smtplib.SMTP(self.config.smtpserver)
		except (socket.gaierror, socket.error) as e:
			self.logger.logWarn("MailAction plugin: error when connecting to SMTP server (%s): %s"\
			                    % (self.config.smtpserver, str(e)))
			return
		try:
			server.sendmail(self.from_, [self.to], msg.as_string())
		except (smtplib.SMTPRecipientsRefused, smtplib.SMTPHeloError,
		        smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as e:
			self.logger.logWarn("MailAction plugin: error when sending mail (From: %s, To: %s): %s"\
			                    % (self.from_, self.to, str(e)))
		server.quit()
