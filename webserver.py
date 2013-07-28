#!/usr/bin/python2

import os
import SimpleHTTPServer
import SocketServer
import posixpath
import urllib
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

		class Server(SocketServer.TCPServer):
			allow_reuse_address = True

		class Handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
			def translate_path(self, path):
				path = path.split('?',1)[0]
				path = path.split('#',1)[0]
				path = posixpath.normpath(urllib.unquote(path))
				words = path.split('/')
				words = filter(None, words)
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
		log.info("Start serving '%s' at port %i" % (self.subdir, self.port))

	def stop(self):
		log.info("Stop serving '%s' at port %i" % (self.subdir, self.port))
		self.httpd.shutdown()
		self.httpd.server_close()
		self.t.join()
