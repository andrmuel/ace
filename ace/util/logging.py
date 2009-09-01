#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Provides logging functions.
"""

import syslog
import sys
import os

class Logger:
	"""
	Can be used to log messages to stderr and the syslog, according to the configuration.
	"""
	def __init__(self, config):
		self.config = config
		if self.config.daemon:
			syslog.openlog(self.config.logident, syslog.LOG_PID, syslog.LOG_DAEMON)
		else:
			syslog.openlog(self.config.logident, syslog.LOG_PID, syslog.LOG_USER)
		self.log_debug = (self.config.loglevel>=5) or (self.config.verbosity>=5)
		self.logDebug("Logging initialized.")

	def logErr(self, message):
		"""
		Log with internal level 1, resp. LOG_ERR.
		"""
		self.log(1, message)
	
	def logWarn(self, message):
		"""
		Log with internal level 2, resp. LOG_WARNING.
		"""
		self.log(2, message)

	def logNotice(self, message):
		"""
		Log with internal level 3, resp. LOG_NOTICE.
		"""
		self.log(3, message)

	def logInfo(self, message):
		"""
		Log with internal level 4, resp. LOG_INFO.
		"""
		self.log(4, message)
	
	def logDebug(self, message, *args):
		"""
		Log with internal level 5, resp. LOG_DEBUG.

		Since this function may be called very often, it takes additional
		arguments, which will be printed after the message itself. This has the
		advantage that objects don't have to be converted to strings, if the
		message is not going to be printed.

		Additionally, logDebug automatically prints the file name, line number
		and function name before the message.
		"""
		if not self.log_debug:
			return
		for arg in args:
			message += str(arg)
		frame = sys._getframe(1)
		filename = os.path.basename(frame.f_code.co_filename)
		funcname = frame.f_code.co_name
		lineno = str(frame.f_lineno)
		self.log(5, "%s[%s]:%s: %s" % (filename, lineno, funcname, message))

	def log(self, level, message):
		"""
		Does the actual logging through the syslog module.
		
		@param level: 1 (highest priority) to 5 (lowest priority)
		@param message: the log message
		"""
		# priority
		if level <= 1:
			priority = syslog.LOG_ERR
		elif level == 2:
			priority = syslog.LOG_WARNING
		elif level == 3:
			priority = syslog.LOG_NOTICE
		elif level == 4:
			priority = syslog.LOG_INFO
		else:
			priority = syslog.LOG_DEBUG
		# logging
		if level <= self.config.loglevel:
			syslog.syslog(priority, message)
		# output to stderr
		if level <= self.config.verbosity and not self.config.daemon:
			sys.stderr.write('-'*level+"> "+message+"\n")
	
	def close(self):
		"""
		Stop logging.
		"""
		self.logDebug("Closing logfile.")
		syslog.closelog()


