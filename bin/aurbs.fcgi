#!/usr/bin/python

import os

from flup.server.fcgi import WSGIServer
#from wsgigzip import GzipMiddleware
from werkzeug.contrib.fixers import LighttpdCGIRootFix
from aurbs.ui.application import app

if __name__ == '__main__':
	app.debug = True
	app.use_x_sendfile = True
	ui_folder = '/usr/share/aurbs/ui'
	app.static_folder = os.path.join(ui_folder, 'static')
	app.template_folder = os.path.join(ui_folder, 'templates')
	#app = GzipMiddleware(app)
	app = LighttpdCGIRootFix(app)
	WSGIServer(app).run()
