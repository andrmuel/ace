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
import csv
import datetime
import time
# own code
from ace.translators.input.base import InputTranslator
from ace.event import Event

class CSVDumpTranslator(InputTranslator):
	"""
	Translation of input from a CSV database dump.

	This translator has use for simulation and testing only. The input should
	already be sorted by DB date.

	Options:
	 - overwrite_arrival: 'true' or 'false' -> overwrite arrival time from CSV
	   field DB_DATE with actual arrival time?
	"""

	FIELDS_REQUIRED = set(["SHORT_NAME", "NAME", "LOG_DATE", "DB_DATE", "MESSAGE"])
	TIMEFORMAT = "%Y-%m-%d %H:%M:%S"

	def __init__(self, num, config, logger):
		InputTranslator.__init__(self, num, config, logger)
		self.leftover = ""
		self.firstline = True
		self.fields = None
		self.overwrite_arrival = False
		if self.options.has_key("overwrite_arrival"):
			if self.options['overwrite_arrival'] == "true":
				self.overwrite_arrival = True
		self.last_arrival_time = 0
		self.sort_warning_done = False

	def translate(self, inputdata):
		"""
		Translate CSV data into events.
		"""
		inputdata = self.leftover + inputdata
		lines = inputdata.split('\n')
		reader = csv.reader(lines[:-1])
		self.leftover = lines[-1]
		for csvline in reader:
			if self.firstline: # assume first line contains header
				self.firstline = False
				self.fields = csvline # -> input independent of column order in csv file
				if not self.FIELDS_REQUIRED.issubset(set(self.fields)):
					self.raiseException(
					  "The following fields are required in the CSV file: %s."
					    % list(self.FIELDS_REQUIRED)
					)
			else:
				logmsg = dict(zip(self.fields, csvline))
				logdate = self.datestr2unixtime(logmsg['LOG_DATE'])
				if self.overwrite_arrival:
					dbdate = int(time.time())
				else:
					dbdate = self.datestr2unixtime(logmsg['DB_DATE'])
					if dbdate < self.last_arrival_time and not self.sort_warning_done:
						self.logger.logWarn("csvdump translator: input not sorted according to DB date - results may be bogus.")
						self.sort_warning_done = True
					else:
						self.last_arrival_time = dbdate
				evt = Event(
				  name=logmsg['SHORT_NAME'],
				  host=logmsg['NAME'],
				  attributes={'log':logmsg["MESSAGE"]},
				  creation=logdate,
				  arrival=dbdate)
				if logmsg.has_key('INTERNAL_CODE'):
					evt.setAttribute('service', logmsg['INTERNAL_CODE'])
				yield evt

	def datestr2unixtime(self, datestr):
		"""
		Converts a date string from the format specified above into a Unix
		timestamp.
		"""
		timeval = datetime.datetime.strptime(datestr, self.TIMEFORMAT)
		return int(timeval.strftime("%s"))
