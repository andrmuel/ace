#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Contains the master class, which manages threads.
"""

import signal
import time
import Queue
import sys

from ace.util import configuration
from ace.util import logging
from ace.util.help import Help
from ace.io import sources
from ace.io import sinks
from ace import core
from ace import ticker
from ace import rpc
from ace import event

class Master:
	"""
	This is the master class. It has the following tasks:
	 - create input and output queues
	 - create a thread for each source
	 - create a thread for each sink
	 - create a ticker instance
	 - create a thread with a running correlation engine core
	 - start all threads
	 - wait for possible commands or until the threads finish

	The main work is done in run(). A description of the execution modes can
	also be found there.
	"""

	def __init__(self, config=None, aftercrash=False):
		self.aftercrash = aftercrash
		self.stop_processing = False
		# configuration
		if config == None:
			self.config = configuration.Config()
		else:
			self.config = config
		# logging
		self.logger = logging.Logger(self.config)
		self.logger.logNotice("Starting ace (a correlation engine).")
		# number of inputs and outputs
		self.num_inputs = len(self.config.input)
		self.num_outputs = len(self.config.output)
		self.logger.logInfo("CE has %d source(s) and %d sink(s)." % (self.num_inputs, self.num_outputs))
		# queues (-> output needs a separate queue for each sink)
		self.input_queue = Queue.Queue(self.config.input_queue_max_size)
		self.output_queues = [Queue.Queue(self.config.output_queue_max_size)
		                      for i in range(self.num_outputs)]
		# ticker
		self.ticker = ticker.Ticker(self.config, self.logger)
		# input
		self.sources = []
		for i in range(self.num_inputs):
			source = sources.get_source(self.config.input[i]['source'].split(':')[0])
			self.sources.append(source(i, self.config, self.logger, self.input_queue))
		# core
		self.core = core.EventHandler(self.config,
		                              self.logger,
		                              self.ticker,
		                              self.input_queue,
		                              self.output_queues)
		# output
		self.sinks = []
		for i in range(self.num_outputs):
			sink = sinks.get_sink(self.config.output[i]['sink'].split(':')[0])
			if self.config.simulation:
				sink.daemon = True  # lets ace exit, in case the core crashes
			self.sinks.append(sink(i, self.config, self.logger, self.output_queues[i]))
		# set up signal handlers
		signal.signal(signal.SIGHUP, self.sighupHandler)        # initiates a rule reload
		signal.signal(signal.SIGTERM, self.sigtermHandler)      # initiates a CE shutdown
		signal.signal(signal.SIGINT, self.sigintHandler)        # initiates an immediate CE shutdown
		# initialise RPC server if requested
		if self.config.rpcserver:
			self.rpchandler = rpc.RPCHandler(self.config, self.logger, self, self.core)

	def getContent(self):
		"""
		Content from Master for RPC clients.
		"""
		def optstr(options):
			"""
			Rebuilds the option string.
			"""
			return ", ".join(["%s=%s" % i for i in options.iteritems()])
		return [
		  {
		    'title': "Configuration",
		    'type': "list",
		    'content': [
		      "Host name: %s" % self.config.hostname,
		      "Rule source: %s" % self.config.rulesource,
		      "Daemon mode: %s" % str(self.config.daemon),
		      "Real-time operation: %s" % str(self.config.realtime),
		      "Simulation mode: %s" % str(self.config.simulation),
		      "Fast exit: %s" % str(self.config.fast_exit),
		      "Log identity: %s" % self.config.logident,
		      "Log level: %s" % str(self.config.loglevel),
		      "Verbosity: %s" % str(self.config.verbosity),
		    ]
		  },{
		    'title': "Sources",
		    'type': "table",
		    'headers': ["Number", "Type", "Options", "Translator", "Translator options", "Alive"],
		    'content': [[
		      source.num,
		      source.name,
		      optstr(source.options),
		      source.translator_name,
		      optstr(source.translator.options),
		      source.isAlive()
		    ] for source in self.sources]
		  },{
		    'title': "Input queue",
		    'type': "table",
		    'headers': ["Number of events in queue", "Maximum size", "Action"],
		    'content': [[
		      self.input_queue.qsize(),
		      self.config.input_queue_max_size,
		      [{'action': "show_inputqueue", 'text': "show", 'args': {}}]
		    ]]
		  },{
		    'title': "Core",
		    'type': "table",
		    'headers': ["Alive"],
		    'content': [[self.core.isAlive()]]
		  },{
		    'title': "Output queues",
		    'type': "table",
		    'headers': ["Number", "Number of events in queue", "Maximum size", "Action"],
		    'content': [[
		      i,
		      self.output_queues[i].qsize(),
		      self.config.output_queue_max_size,
		      [{'action': "show_outputqueue", 'text': "show", 'args': {'num': str(i)}}]
		    ] for i in range(len(self.output_queues))]
		  },{
		    'title': "Sinks",
		    'type': "table",
		    'headers': ["Number", "Type", "Options", "Translator", "Translator options", "Alive"],
		    'content': [[
		      sink.num,
		      sink.name,
		      optstr(sink.options),
		      sink.translator_name,
		      optstr(sink.translator.options),
		      sink.isAlive()
		    ] for sink in self.sinks]
		  }
		]

	def sighupHandler(self, signal, frame):
		"""
		Initiates a rule reload upon SIGHUP (-> 'killall -HUP ace').
		"""
		self.logger.logDebug("Caught SIGHUP - requesting rule reload from core.")
		self.core.reloadRules()

	def sigtermHandler(self, signal, frame):
		"""
		Initiates stop upon SIGTERM (-> 'killall ace').
		"""
		self.logger.logInfo("Caught SIGTERM - ace will be stopped.")
		self.finish()

	def sigintHandler(self, signal, frame):
		"""
		Initiates an immediate stop upon SIGINT (-> CTRL-C).
		"""
		self.logger.logNotice("Master: Caught SIGINT - ace will be stopped immediately.")
		sys.exit(1)

	def finish(self):
		"""
		Stops the CE in an ordered fashion.
		"""
		self.logger.logInfo("Stopping ace.")
		# stop RPC server
		if self.config.rpcserver:
			if self.config.simulation and not self.config.fast_exit and not self.config.daemon:
				raw_input("Hit enter to exit.\n") # allow introspection after simulation
			self.logger.logDebug("Shutting down RPC server.")
			self.rpchandler.shutdown()
			self.rpchandler.join()
			self.logger.logDebug("RPC server joined.")
		# stop sources
		for source in self.sources:
			if source.is_alive() or self.config.simulation:
				source.finish()
				if not self.config.simulation:
					source.join()
			else:
				self.logger.logWarn("Master: source %d (%s) thread died." % (source.num, source.name))
		# send event indicating the shutdown
		if not self.config.simulation:
			self.input_queue.put(event.Event(name="CE:SHUTDOWN",
			                                 type="internal",
			                                 local=True,
			                                 description="Ace was stopped.",
			                                 host=self.config.hostname))
		# join input queue
		if not self.config.fast_exit and not self.config.simulation:
			self.logger.logInfo("Master: slow exit - waiting until all events "\
			                   +"in input queue have been processed.")
			while self.core.is_alive() and self.input_queue.unfinished_tasks>0:
				time.sleep(self.config.thread_sleep_time)
			if self.core.is_alive():
				self.input_queue.join()
				self.logger.logInfo("Master: input queue joined - all events processed.")
		# stop core
		if self.core.is_alive() or self.config.simulation:
			self.core.finish()
			if not self.config.simulation:
				self.core.join()
		else:
			self.logger.logWarn("Master: core thread died.")
		# join output queues
		if not self.config.fast_exit:
			self.logger.logInfo("Master: slow exit - waiting until all events "\
			                   +"in output queues have been processed.")
			for i in range(len(self.output_queues)):
				while self.sinks[i].is_alive() and self.output_queues[i].unfinished_tasks>0:
					time.sleep(self.config.thread_sleep_time)
				if self.sinks[i].is_alive():
					self.output_queues[i].join()
					self.logger.logInfo("Master: output queue %d joined - all events forwarded." % i)
		# stop sinks
		for sink in self.sinks:
			if sink.is_alive():
				sink.finish()
				sink.join()
			else:
				self.logger.logWarn("Master: sink %d (%s) thread died." % (sink.num, sink.name))
		self.stop_processing = True

	def allThreadsAlive(self):
		"""
		Checks if all child threads are alive.	
		"""
		if not self.config.simulation:
			for source in self.sources:
				if not source.is_alive():
					return False
			if not self.core.is_alive():
				return False
		for sink in self.sinks:
			if not sink.is_alive():
				return False
		return True

	def checkSimulationDone(self):
		"""
		Checks if we can finish the simulation. This is the case when:
		
		 - the input queue is empty
		 - the core has no more events in its internal queue
		 - there are no more contexts, which may generate further events
		 - there are no more delayed events in the cache
		"""
		if self.input_queue.qsize() > 0:
			return False
		if len(self.core.generated_input_events) > 0:
			return False
		if self.core.contextmanager.mayGenerateTimeoutEvents():
			return False
		if self.core.cache.hasDelayedEvents():
			return False
		return True

	def run(self):
		"""
		The main work function. Note that there are three execution modes:
		 - in simulation mode, the master controls the execution of the
		   threads, and the simulation exits, when all input has been processed 
		 - in debugging mode, the threads run independently, a console is
		   started, and the execution stops, when the user exits from the
		   console 
		 - in the normal mode, the correlation engine runs indefinitely, until
		   it receives a SIGTERM
		"""
		# log
		self.logger.logInfo("Master: running.")
		# send event indicating the start
		if not self.config.simulation:
			self.input_queue.put(event.Event(name="CE:STARTUP",
			                                 type="internal",
			                                 local=True,
			                                 description="Ace was started.",
			                                 host=self.config.hostname))
			if self.aftercrash:
				self.input_queue.put(event.Event(name="CE:STARTUP:AFTERCRASH",
				                                 type="internal",
				                                 local=False,
				                                 description="Ace was started after an unclean shutdown.",
				                                 host=self.config.hostname))
		# start all required threads
		if not self.config.simulation: # simulation -> master controls input and core
			self.logger.logInfo("Master: starting source thread(s).")
			for source in self.sources:
				source.start()
			self.logger.logInfo("Master: starting core thread.")
			self.core.start()
		self.logger.logInfo("Master: starting sink thread(s).")
		for sink in self.sinks:
			sink.start()
		if self.config.rpcserver:
			self.rpchandler.start()
		# main loop -> depends on execution mode
		if self.config.simulation:
			# simulation
			# -> master controls execution
			# input from sources:
			self.logger.logInfo("Master: simulation: asking source(s) for input.")
			for source in self.sources:
				source.work()
			if not self.config.realtime:
				if not self.input_queue.empty():
					self.ticker.firsttick = self.input_queue.queue[0].getArrivalTime()
					self.ticker.tick = self.ticker.firsttick
			# actual simulation
			self.logger.logNotice("Master: starting simulation at tick %d." % self.ticker.getTick())
			while not (self.stop_processing or self.checkSimulationDone()):
				self.logger.logDebug("Simulation: asking core to process events.")
				self.core.work()
			self.logger.logNotice("Master: simulation ended at tick %d." % self.ticker.getTick())
			self.finish()
		elif self.config.python_console or self.config.ipython_console:
			# debugging mode 
			# -> run until the user exits from the console
			self.logger.logInfo("Master: starting console for interaction.")
			help = Help()
			if self.config.python_console:
				import code
				interpreter = code.InteractiveConsole(globals())
				interpreter.interact("Starting Python console ('help' shows usage) ...")
			else:
				try:
					from IPython.Shell import IPShellEmbed
					ipshell = IPShellEmbed("",
					                       banner="Starting IPython ('help' shows usage) ...",
					                       exit_msg="Leaving IPython ...")
					ipshell()
				except ImportError:
					self.logger.logErr("Start of IPython console requested,"\
					  +" but import failed (this most likely means IPython is"\
					  +" not installed; please try starting the Python console"\
					  +" instead).")
			self.logger.logInfo("Console closed - ace will be stopped.")
			self.finish()
		else:
			# normal mode
			# -> wait forever (or shorter, if a SIGTERM initiates a shutdown,
			# or a thread crashes)
			self.logger.logInfo("Master: waiting for events or SIGTERM.")
			while not self.stop_processing:
				if not self.allThreadsAlive():
					# thread died 
					# -> exit
					# (note: we could also try to restart the affected thread)
					self.logger.logErr("Master: a child thread died - exiting.")
					self.finish()
				time.sleep(self.config.thread_sleep_time)
		# events may be left in the queues
		if self.input_queue.qsize() > 0:
			self.logger.logInfo("Master: "+str(self.input_queue.qsize())+" events left in input queue.")
		for i in range(len(self.output_queues)):
			if self.output_queues[i].qsize() > 0:
				self.logger.logInfo("Master: %d events left in output queue %d."\
				                    % (self.output_queues[i].qsize(), i))
		# all done
		self.logger.logNotice("All threads finished - exiting.")
		self.logger.close()

# main function - for testing only
if __name__ == '__main__':
	config = configuration.Config(ipython_console=True)
	master = Master(config)
	master.run()
