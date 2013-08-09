#!/usr/bin/env python

import os
import sys
from flask import Flask, render_template, request, redirect, url_for

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))
from aurbs import dummy
from aurbs.db import Database
from aurbs.config import AurBSConfig
from aurbs.static import *
from aurbs.helper import *

app = Flask(__name__)
AurBSConfig("/etc/aurbs.yml")
db = Database()

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
	return value.strftime(format)

@app.route('/')
def index():
	return render_template("base.html")

@app.route('/status')
def status():
	return "Status monitor"

@app.route("/problems")
def problems():
	pkgs_failed = db.get_results(rtype='problem', type='fail')
	pkgs_notinaur = db.get_results(rtype='problem', type='not_in_aur')
	pkgs_depmiss = db.get_results(rtype='problem', type='missing_depends')
	pkgs_blocked = db.get_results(rtype='problem', type='blocked_depends')
	return render_template("problems.html", pkgs_failed=pkgs_failed, pkgs_notinaur=pkgs_notinaur, pkgs_depmiss=pkgs_depmiss, pkgs_blocked=pkgs_blocked)

@app.route("/packages")
@app.route("/packages/")
def package_list():
	pkgs = []
	query = request.args.get('query', None)
	for pkgname in AurBSConfig().aurpkgs:
		try:
			pkg = db.get_pkg(pkgname)
		except KeyError:
			pkg = dummy.aurpkg(pkgname)
		if query:
			if query not in pkg['name']:
				continue
		pkgs.append(pkg)
	if query and len(pkgs) == 1:
		return redirect(url_for('package_view', pkgname=pkgs[0]['name']))
	pkgs = sorted(pkgs, key=lambda i: i['name'])
	return render_template("package_list.html", pkgs=pkgs)

@app.route("/packages/<pkgname>")
def package_view(pkgname):
	if pkgname not in AurBSConfig().aurpkgs:
		pass
		#return "package not found"
	try:
		pkg = db.get_pkg(pkgname)
	except KeyError:
		pkg = dummy.aurpkg(pkgname)
	results = {}
	builds = {}
	for arch in pkg['arch']:
		results[arch] = db.get_result(pkgname, arch)
		results[arch] = {'rtype': 'scheduled'} if not results[arch] else results[arch]
		try:
			builds[arch] = find_pkg_files(pkgname, os.path.join(AurBSConfig()['public_repo']['local_path'], arch))[0]
		except (IndexError, FileNotFoundError):
			pass
	local_depends = filter_dependencies([pkg['depends']], local=True)
	required_by = db.get_pkg_required_by(pkgname)
	return render_template("package_view.html", pkg=pkg, results=results, local_depends=local_depends, required_by=required_by, builds=builds, repo_url=AurBSConfig()['public_repo']['http_url'])

if __name__ == '__main__':
	try:
		app.secret_key = open("secret.key", 'b').read()
	except:
		app.secret_key = os.urandom(24)
		open("secret.key", 'wb').write(app.secret_key)
	app.debug = True
	app.run(host="0.0.0.0", port=80)
