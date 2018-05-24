#!/usr/bin/env python

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, send_file, send_from_directory

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))
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
	repo_name = AurBSConfig().public_repo['name']
	try:
		repo_url = AurBSConfig().public_repo['http_url']
	except KeyError:
		repo_url = url_for('public_repo', _external=True)
	return render_template("base.html", repo_name=repo_name, repo_url=repo_url)

@app.route('/status')
def status():
	return render_template("status.html", status=db.get_status())

@app.route('/status.json')
def status_json():
	return jsonify(db.get_status())

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
	try:
		pkg = db.get_pkg(pkgname)
	except KeyError:
		pkg = dummy.aurpkg(pkgname)
	building_arch = None
	try:
		status = db.get_status()
		if status['building'] == pkgname:
			building_arch = status['arch']
	except KeyError:
		pass
	results = {}
	builds = {}
	for arch in pkg['arch']:
		if building_arch == arch or building_arch is not None and arch == 'any':
			results[arch] = {'rtype': 'building', 'rvalue': {'name': pkgname, 'build_arch': building_arch}}
		else:
			results[arch] = db.get_result(pkgname, build_arch=arch)
		if not results[arch]:
			if arch in AurBSConfig().architectures or arch == 'any':
				results[arch] = {'rtype': 'scheduled'}
			else:
				results[arch] = {'rtype': 'disabled'}
		try:
			builds[arch] = find_pkg_files(pkg.get('splitpkgs', pkgname), directory=repodir(arch))
		except (IndexError, FileNotFoundError):
			pass
	local_depends = db.filter_dependencies([pkg['depends']], local=True)
	required_by = db.get_pkg_required_by(pkgname)
	return render_template("package_view.html", pkg=pkg, results=results, local_depends=local_depends, required_by=required_by, builds=builds)

@app.route("/packages/<pkgname>/<build_arch>/log")
def package_log(pkgname, build_arch):
	try:
		pkg = db.get_pkg(pkgname)
	except KeyError:
		return "pkg not found"
	try:
		status = db.get_status()
		if status['building'] == pkgname and status['arch'] == build_arch:
			building = True
		else:
			building = False
	except:
		building = False
	return render_template("package_log.html", pkg=pkg, build_arch=build_arch, building=building)

@app.route("/packages/<pkgname>/<build_arch>/log.txt")
def package_log_txt(pkgname, build_arch):
	try:
		pkg = db.get_pkg(pkgname)
	except KeyError:
		return "pkg not found"
	logfile = os.path.join(build_dir(build_arch), pkgname, "makepkg.log")
	if os.path.exists(logfile):
		seek = int(request.args.get('seek', -1))
		f = open(logfile, 'rb')
		if seek != -1:
			f.seek(seek)
			logstr = f.read()
			# prevent x-sendfile as it doesn't support seeking
			return Response(logstr, content_type="text/plain", direct_passthrough=True)
		else:
			return send_file(f, mimetype="text/plain", add_etags=True, conditional=True)
	else:
		return "log not found"

@app.route("/aurstaging/<arch>/<pkg>")
def aurstaging_get(arch, pkg):
	if arch not in AurBSConfig().architectures and arch != 'any':
		return "404"
	else:
		return send_from_directory(repodir(arch), pkg)

@app.route("/%s/<arch>/<pkg>" % AurBSConfig().public_repo['name'])
def public_repo_get(arch, pkg):
	if arch not in AurBSConfig().architectures and arch != 'any':
		return "invalid arch"
	else:
		return send_from_directory(repodir_public(arch), pkg)

@app.route("/%s" % AurBSConfig().public_repo['name'])
def public_repo():
	return "no directory listing using internal webserver"

try:
	app.secret_key = open("/tmp/aurbs.secret.key", 'b').read()
except:
	app.secret_key = os.urandom(24)
	open("/tmp/aurbs.secret.key", 'wb').write(app.secret_key)
	os.chmod("/tmp/aurbs.secret.key", 0o600)

if __name__ == '__main__':
	app.debug = True
	app.run(host="0.0.0.0", port=80)
