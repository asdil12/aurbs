#!/usr/bin/python

from flup.server.fcgi import WSGIServer
#from wsgigzip import GzipMiddleware
from werkzeug.contrib.fixers import LighttpdCGIRootFix
from application import app
import os

cwd = os.path.abspath(os.path.dirname(__file__))
os.chdir(cwd)

if __name__ == '__main__':
	app.debug = True
	app.use_x_sendfile = True
	#app = GzipMiddleware(app)
	app = LighttpdCGIRootFix(app)
	WSGIServer(app).run()
