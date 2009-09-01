#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
CSV log rewriter.
"""

from optparse import OptionParser
import csv
import datetime
import time
import sys
import string
import itertools

class LogRewriter:
	FIELDS = ["SHORT_NAME", "NAME", "LOG_DATE", "DB_DATE", "MESSAGE", "INTERNAL_CODE"]
	def __init__(self, infile, outfile, move_to=None, scale_to=None, anonymize=False):
		self.infile = infile
		self.outfile = outfile
		self.move_to = move_to
		self.scale_to = scale_to
		self.anonymize = anonymize
		self.firstline = True
		self.timeformat = "%Y-%m-%d %H:%M:%S"
	
	def run(self):
		entries = self.read_entries()
		entries.sort(key=lambda entry: entry['DB_DATE'])
		self.shift_and_scale(entries)
		self.write_entries(entries)

	def read_entries(self):
		lines = [line[:-1] for line in self.infile.readlines()]
		reader = csv.reader(lines)
		entries = []
		for csvline in reader:
			if self.firstline: # assume first line contains header
				self.firstline = False
				self.fields = csvline # -> input independent of column order in csv file
			else:
				entries.append(dict(zip(self.fields,csvline)))
				entries[-1]['LOG_DATE'] = self.datestr2unixtime(entries[-1]['LOG_DATE'])
				entries[-1]['DB_DATE'] = self.datestr2unixtime(entries[-1]['DB_DATE'])
		return entries

	def shift_and_scale(self, entries):
		first_log = min(entry['LOG_DATE'] for entry in entries)
		first_db = min(entry['DB_DATE'] for entry in entries)
		# first = min(first_log, first_db)
		first = first_db
		if self.move_to != None:
			shift_by = self.move_to - first
		else:
			shift_by = 0
		if self.scale_to != None:
			last_log = max(entry['LOG_DATE'] for entry in entries)
			last_db = max(entry['DB_DATE'] for entry in entries)
			# last = min(last_log, last_db)
			last = last_db
			scale_by = float(self.scale_to)/float(last-first)
		else:
			scale_by = 1
		if self.anonymize:
			hosts = list(set([entry['NAME'] for entry in entries]))
			letters = itertools.product(['']+list(string.lowercase), ['']+list(string.lowercase), string.lowercase)
			anon_names = {}
			for host in hosts:
				if not host in anon_names:
					anon_name = "host-"+"".join(letters.next())
					cluster_name = host
					if host.endswith("-1") or host.endswith("-2") or host.endswith("-3") or host.endswith("-4"):
						host = host[:-2]
						for i in range(1,5):
							anon_names[host+"-%d"%i] = anon_name+"-%d"%i
					else:
						anon_names[host] = anon_name
			self.fields = self.FIELDS
		for entry in entries:
			entry['LOG_DATE'] = self.unixtime2datestr(int((entry['LOG_DATE']-first)*scale_by + first + shift_by))
			entry['DB_DATE'] = self.unixtime2datestr(int((entry['DB_DATE']-first)*scale_by + first + shift_by))
			if self.anonymize:
				entry['NAME'] = anon_names[entry['NAME']]
				# entry['MESSAGE'] = entry['MESSAGE'].replace(hostname, entry['NAME'])
				entry['MESSAGE'] = ""

	def write_entries(self, entries):
		writer = csv.writer(self.outfile)
		writer.writerow(self.fields)
		for entry in entries:
			writer.writerow([entry[field] for field in self.fields])

	def datestr2unixtime(self,datestr):
		d = datetime.datetime.strptime(datestr, self.timeformat)
		return int(d.strftime("%s"))

	def unixtime2datestr(self, unixtime):
		d = datetime.datetime.fromtimestamp(unixtime)
		return d.strftime(self.timeformat)

if __name__ == '__main__':
	# parse options
	parser = OptionParser(usage="usage: %prog [options] inputfile [outputfile]")
	parser.add_option("-a", "--anonymize-hosts", dest="anonymize", action="store_true", help="anonymize host names")
	parser.add_option("-s", "--scale-to", action="store", type="int", dest="scale", help="scale timestamps, such that they span over the given time period in minutes")
	parser.add_option("-m", "--move-to", action="store", type="int", dest="move_to", help="move timestamps, so the first timestamp is at the given position (Unix timestamp)")
	parser.add_option("-M", "--move-relative", action="store", type="int", dest="move_relative", help="move timestamps, so the first timestamp is at the given position relative to the current time (seconds)")
	(options,args) = parser.parse_args()
	kwargs = {}
	if len(args)<1:
		parser.print_help()
		sys.exit(1)
	if options.anonymize:
		kwargs['anonymize'] = True
	if options.scale != None:
		kwargs['scale_to'] = 60*options.scale
	if options.move_to != None:
		kwargs['move_to'] = options.move_to
	if options.move_relative != None:
		kwargs['move_to'] = options.move_relative + int(time.time())
	# open files
	inputfile = open(args[0], 'r')
	if len(args)>1:
		outputfile = open(args[1], 'w')
	else:
		outputfile = sys.stdout
	# run rewriter
	rewriter = LogRewriter(inputfile, outputfile, **kwargs)
	rewriter.run()
	# close files
	inputfile.close()
	outputfile.close()
