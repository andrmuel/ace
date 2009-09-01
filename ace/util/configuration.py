#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
configuration module - implements a class to manage configuration information.
"""

import sys
import os
import re
import syslog
import socket

import ace

class Config:
	"""
	A class with configuration information.
	"""

	STRUCTURE = {
	  'main': {
	    'events_dtd'            : 'string',
	    'rules_dtd'             : 'string',
	    'lockfile'              : 'string',
	    'rulesource'            : 'string',
	    'classlist'             : 'string',
	    'hostname'              : 'string',
	    'daemon'                : 'bool',
	    'realtime'              : 'bool',
	    'simulation'            : 'bool',
	    'fast_exit'             : 'bool',
	    'cache_max_size'        : 'int',
	    'thread_sleep_time'     : 'float',
	    'rpcserver'             : 'bool',
	    'rpcserver_host'        : 'string',
	    'rpcserver_port'        : 'int',
	    'input_queue_max_size'  : 'int',
	    'output_queue_max_size' : 'int',
	    'logident'              : 'string',
	    'loglevel'              : 'int',
	    'verbosity'             : 'int',
	    'python_console'        : 'bool',
	    'ipython_console'       : 'bool',
	    'smtpserver'            : 'string'
	  },
	  'input': {
	    'translator' : 'string',
	    'source'     : 'string'
	  },
	  'output': {
	    'translator' : 'string',
	    'sink'       : 'string'
	  }
	}

	BOOL_VALUES = {
	  'no'    : False,
	  'false' : False,
	  '0'     : False,
	  'yes'   : True,
	  'true'  : True,
	  '1'     : True
	}

	# general stuff
	etc = os.path.dirname(ace.__file__)+"/etc/"

	# configfile = "/etc/ace/ace.conf"#: configuration file location
	configfile = "/etc/ace/ace.conf"#: configuration file location
	events_dtd = etc+"events.dtd"   #: location of the file with the DTD for events
	rules_dtd = etc+"rules.dtd"     #: location of the file with the DTD for correlation rules
	lockfile = "/var/lock/ace-lockfile" #: location of the lock file for daemon mode
	rulesource = "file:filename="+etc+"emptyrules.xml" #: source of correlation rules
	classlist = "file:filename="+etc+"emptyclasses.xml" #: source of event classes
	hostname = socket.gethostname() #: name of the host, where the CE is running 
	daemon = False                  #: daemonize the application?
	realtime = True                 #: bind internal time to real time? (this means, one tick will be equal to one second. otherwise, the next tick starts as soon as all processing for the current tick is done.)
	simulation = False              #: if True, the master control the execution of the input threads and the core, to guarantee an ordered execution for simulation. Note: in simulation mode, source and core threads must not be started!
	fast_exit = False               #: if True, the CE will exit faster, but it is not guaranteed that the queues are empty when the CE exits
	cache_max_size = 10000          #: maximum number of events in the cache
	thread_sleep_time = 0.1         #: time in seconds, how long a thread sleeps, if there is no work
	rpcserver = False               #: whether to start an RPC server for remote control
	rpcserver_host = "localhost"    #: host for RPC server
	rpcserver_port = 1070           #: port for RPC server
	
	# input/output configuration
	input_queue_max_size = 100000   #: maximum number of events in the input queue
	output_queue_max_size = 10000   #: maximum number of events in the output queue
	input = [{
	  'source': 'file',           #: a source from io.sources -> format: sourcename:option1=value1:option2=value2:..  default: use STDIN
	  'translator': 'letter'      #: a translator from translators.input -> format: translatorname:option1=value1:option2=value2:.. 
	}]
	output = [{
	  'sink': 'file',             #: a sink from io.sinks -> format: sinkname:option1=value1:option2=value2:.. default: use STDOUT
	  'translator': 'linebased'   #: a translator from translators.output -> format: translatorname:option1=value1:option2=value2:.. 
	}]
	
	# logging/verbosity for status messages
	logident = "ace"            #: ident string for syslog messages 
	loglevel = 3                #: quantity of logging (0: nothing 1: errors only 2: errors and warnings 3: errors, warnings, notices, 4: additionally informational messages 5: everything, including debug information, i.e. *many* messages)
	verbosity = 3               #: verbosity for printing to stderr (same numbering as loglevel, but nothing is printed if the application is running as daemon)

	# consoles for debugging
	python_console = False      #: start an interactive Python console for debugging?
	ipython_console = False     #: start an interactive IPython console for debugging? 

	# plugin configuration
	smtpserver = "localhost"    #: SMTP server for mail action plugin

	def __init__(self, filename=None, daemon=None, rulesource=None, rpcserver=None, python_console=None, ipython_console=None, verbose=None):
		# config file parsing ...
		config = self.parseConfigFile(filename)
		# store values ...
		for section in config:
			if section == 'main':
				for group in config[section]:
					for key, value in group.iteritems():
						setattr(self, key, value)
			elif section=='input':
				for group in config[section]:
					if not (group.has_key('source') and group.has_key('translator')):
						self.exitError("'input' section needs source and translator.")
				self.input = config[section]
			else:
				for group in config[section]:
					if not (group.has_key('sink') and group.has_key('translator')):
						self.exitError("'output' section needs sink and translator.")
				self.output = config[section]
		# config from arguments
		if daemon != None:
			self.daemon = bool(daemon)
		if rulesource != None:
			self.rulesource = rulesource
		if rpcserver != None:
			self.rpcserver = bool(rpcserver)
		if python_console != None:
			self.python_console = bool(python_console)
		if ipython_console != None:
			self.ipython_console = bool(ipython_console)
		if verbose != None:
			self.verbosity += verbose

	def parseConfigFile(self, filename):
		"""
		Try to parse the configuration file.
		
		@param filename: name of config file given as argument
		"""
		# local variables
		config = {}
		section = 'main'
		linenr = 0
		errors = []
		# location of config file from argument
		if filename != None:
			self.configfile = filename
		# open the file	
		try:
			configfile = open(self.configfile, 'r')
		except IOError, e:
			if filename == None: # no filename was given -> default file not found -> ok
				return config
			else: # given configuration file not found -> error
				self.exitError("Error opening configuration file: "+str(e))
		for line in configfile:
			linenr += 1
			line = line.split('#')[0].strip() # remove comments and leading/trailing whitespace
			if len(line)==0: # ignore empty/comment lines
				continue
			section_match = re.match(r"^\[(?P<section>\w+)\]$", line)
			option_match = re.match(r"^(?P<key>\w+)\s*=\s*(?P<value>.+)$", line)
			if section_match:
				sec = section_match.group('section').lower()
				if not sec in self.STRUCTURE.keys():
					errors.append((linenr, "Unknown section '"+sec+"'."))
					continue
				section = sec
				if not config.has_key(section):
					config[section] = []
				config[section].append({})
			elif option_match:
				key = option_match.group('key').lower()
				value = option_match.group('value')
				if not self.STRUCTURE[section].has_key(key):
					errors.append((linenr, "Unknown option '"+key+"' for section '"+section+"'."))
					continue
				if self.STRUCTURE[section][key] == 'bool':
					if value.lower() in self.BOOL_VALUES.keys():
						config[section][-1][key] = self.BOOL_VALUES[value.lower()]
					else:
						errors.append((linenr, "Not a bool: '"+value+"'."))
				elif self.STRUCTURE[section][key] == 'int':
					if value.isdigit():
						config[section][-1][key] = int(value)
					else:
						errors.append((linenr, "Not an int: '"+value+"'."))
				elif self.STRUCTURE[section][key] == 'float':
					if re.match(r"^\d+(\.\d*)?$", value):
						config[section][-1][key] = float(value)
					else:
						errors.append((linenr, "Not a float: '"+value+"'."))
				else:
					config[section][-1][key] = value
			else:
				errors.append((0, "Unparseable line: "+line))
		configfile.close()
		if len(errors)>0:
			for error in errors:
				sys.stderr.write(filename+':'+str(error[0])+": "+error[1]+"\n")
			self.exitError("Errors during parsing of configuration file.\n")
		return config

	def exitError(self, msg):
		"""
		Return to shell with an exit status 1 and the given message.
		"""
		sys.stderr.write(msg)
		syslog.openlog("ace") # we don't have a logger yet ...
		syslog.syslog(syslog.LOG_ERR, "Can't start correlation engine (invalid configuration file): "+msg)
		syslog.closelog()
		sys.exit(1)

	def splitLine(self, line):
		"""
		Split a line in the format configentity:option1=value1:option2:value2
		into a name and a dict.
		"""
		entries = line.split(":")
		name = entries[0]
		if len(entries)>0:
			options = dict([entry.split("=") for entry in entries if len(entry.split("="))==2])
		else:
			options = dict()
		return (name, options)

	def configTemplate(self):
		"""
		Returns a string with a template for a configuration file.
		"""
		string = "# ace configuration file\n"
		for section in ['main', 'input', 'output']:
			string += "\n["+section+"]\n"
			for entry in self.STRUCTURE[section]:
				string += entry+" = "
				if section == 'main':
					string += str(getattr(self, entry))
				else:
					string += str(getattr(self, section)[0][entry])
				string += " "*(40-len(string.split("\n")[-1]))+" # "+self.STRUCTURE[section][entry]+"\n"
		return string
