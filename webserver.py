#!/usr/bin/env python

import os
import sys
import http.server
import socketserver
import posixpath
import urllib.request, urllib.parse, urllib.error
import threading
import logging

log = logging.getLogger('aurbs')

class WebServer(object):
	"""
	w = WebServer('aurstaging', 8000)

	import time
	time.sleep(10)

	w.stop()
	"""
	def __init__(self, subdir, port):
		self.subdir = subdir
		self.port = port

		class Server(socketserver.TCPServer):
			allow_reuse_address = True
			def handle_error(self, request, client_address):
				cas = '(%s:%i)' % client_address
				type_, value_, traceback_ = sys.exc_info()
				log.warning('Webserver error handling request from: %s: %s' % (client_address, value_.__repr__()))

		class Handler(http.server.SimpleHTTPRequestHandler):
			def translate_path(self, path):
				path = path.split('?',1)[0]
				path = path.split('#',1)[0]
				path = posixpath.normpath(urllib.parse.unquote(path))
				words = path.split('/')
				words = [w for w in words if w]
				path = os.path.join(os.getcwd(), subdir)
				for word in words:
					drive, word = os.path.splitdrive(word)
					head, word = os.path.split(word)
					if word in (os.curdir, os.pardir): continue
					path = os.path.join(path, word)
				return path
			def log_message(self, format, *args):
				log.debug("web-%i: %s - - %s" % (port, self.client_address[0], format%args))

		self.httpd = Server(('127.0.0.1', self.port), Handler)
		self.t = threading.Thread(target=self.httpd.serve_forever)
		self.t.daemon = True
		self.t.start()
		log.debug("Start serving '%s' at port %i" % (self.subdir, self.port))

	def stop(self):
		log.debug("Stop serving '%s' at port %i" % (self.subdir, self.port))
		self.httpd.shutdown()
		self.httpd.server_close()
		self.t.join()
