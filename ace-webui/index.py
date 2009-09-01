#!/usr/bin/env python
# coding: utf8
#
# Andreas Müller, 2009
# andrmuel@ee.ethz.ch
#
# This code may be freely used under GNU GPL conditions.

"""
Simple WebUI for ace - reuses lxml, since lxml is already a dependency.
"""

import cgi
import xmlrpclib
import socket
import sys
import time
import itertools

from lxml import etree
from lxml.html.builder import *

HTTPHEADER = "Content-type: text/html\n"
HTMLHEADER = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">"""

HOST = "localhost" # RPC server host
PORT = 1070        # RPC server port

class ACEWebUI:
	"""
	Allows control of ace via a browser.
	"""

	location = "index.py"
	menuentries = ['home', 'master', 'core', 'cache', 'contexts', 'rulebase']

	def __init__(self, cgifields):
		self.inittime = time.time()
		self.page = cgifields.getvalue('page') if cgifields.has_key('page') else 'home'
		self.action = cgifields.getvalue('action') if cgifields.has_key('action') else ""
		self.args = dict([(key, cgifields.getvalue(key)) for key in cgifields.keys()])
		self.proxy = xmlrpclib.ServerProxy("http://%s:%d/" % (HOST, PORT), allow_none=True)

	def renderPage(self):
		return etree.tostring(self.pageTree(), pretty_print=True)

	def pageTree(self):
		return HTML({'xmlns': "http://www.w3.org/1999/xhtml"},
		  HEAD(
		    TITLE("ace - a correlation engine"),
			# META({"http-equiv":"refresh", "content":"10; URL=index.py?page=%s"%self.page}) if (self.action=="") else etree.Comment(" action - no reloading "),
		    META({"http-equiv":"content-type", "content":"text/html; charset=utf-8"}),
		    LINK({'href': "default.css", 'rel': "stylesheet", 'type': "text/css"})
		  ),
		  BODY(
		    self.menuTree(),
		    self.headerTree(),
		    self.mainTree(),
		    self.footerTree()
		  )
		)

	def menuTree(self):
		pages = [LI({'class': "active"*(self.page==page)}, A({'href':self.location+"?page="+page}, page)) for page in self.menuentries]
		return DIV({'id': "menu"}, UL(*pages))

	def headerTree(self):
		return DIV({'id': "header"},
		  H1(A({'href': self.location}, "ace - a correlation engine")),
		  H2(A({'href': "#"}, self.page))
		)

	def mainTree(self):
		try:
			stats = self.proxy.getStats()
			main = DIV({'id': "page"})
			if len(stats)>0:
				main.append(DIV({'id': "sidebar"}, DIV({'class': "bluebox"},
				  H2("Statistics:"),
				  UL(*[LI(H3(entry[0]), str(entry[1])) for entry in stats])
				)))
			if len(self.action)>0: # if action, execute it end display result
				content = self.proxy.execAction(self.action, self.args)
			else: # else display content
				content = self.proxy.getContent(self.page)
			main.append(DIV({'id': "content"}, *[self.entryTree(entry) for entry in content]))
			return main
		except socket.error as e:
			return DIV({'class': "post hr"}, BR(), H1("Error connecting to RPC server on port %d" % PORT), "Message from socket: %s" % e)
		except:
			return DIV({'class': "post hr"}, BR(), H1("Unexpected error"), P(str(sys.exc_info()[0])), P(str(sys.exc_info()[1])))

	def entryTree(self, entry):
		if len(entry['content']) == 0:
			return etree.Comment(" empty entry '%s' ignored " % entry['title'])
		if entry['type'] == 'text':
			content = P(*self.textTree(entry['content']))
		elif entry['type']=='pre':
			content = PRE(*self.textTree(entry['content']))
		elif entry['type']=='table':
			tr_class = itertools.cycle([{'class': "odd"}, {'class': "even"}]).next
			td_align = lambda var: {'align': "right" if type(var) == int else "left"}
			content = TABLE(
			  TR(*[TH(header) for header in entry['headers']]),
			  *[TR(tr_class(), *[TD(td_align(col), *self.textTree(col)) for col in row]) for row in entry['content']]
			)
		elif entry['type']=='list':
			content = UL(*[LI(*self.textTree(listentry)) for listentry in entry['content']])
		else:
			content = P("Unknown entry type: %s" % entry['type'])
		return DIV({'class': "post"}, H2(entry['title']), content)

	def textTree(self, content):
		if type(content) == list:
			elements = []
			for element in content:
				if type(element) == dict and set(["action", "args", "text"]).issubset(element.keys()) and type(element['args']) == dict:
					url = "%s?page=%s&action=%s" % (self.location, self.page, element['action'])\
					      +''.join(["&%s=%s"%item for item in element['args'].iteritems()])
					elements.append(A({'href': url}, str(element['text'])))
				else:
					elements.append(str(element))
		else:
			elements = [str(content)]
		return elements

	def footerTree(self):
		return DIV({'id': "footer"},
		  P(
		    u"Andreas Müller, 2009", BR(),
		    "Design: subdued from ", A({'href': "http://freecsstemplates.org"},"freecsstemplates.org"), BR(),
		    "Rendered in %1.3f seconds." % (time.time()-self.inittime)
		  )
		)

if __name__ == '__main__':
	print HTTPHEADER
	print HTMLHEADER
	webui = ACEWebUI(cgi.FieldStorage())
	print webui.renderPage()
