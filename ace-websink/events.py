#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Event query script - gets new events via RPC.
"""

import xmlrpclib
import socket
import json

PORT = 1071

if __name__ == '__main__':
	print "Content-type: text/plain\n"
	try:
		proxy = xmlrpclib.ServerProxy("http://localhost:%d/" % PORT, allow_none=True)
		events = proxy.getEvents()
		print json.dumps([event for event in events])
	except socket.error:
		print json.dumps([])
