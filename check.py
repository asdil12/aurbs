#!/usr/bin/python2

import sys
import subprocess
from pkg_resources import parse_version

import logging
import logging.handlers
import argparse


import aur
import db


parser = argparse.ArgumentParser(description='AUR Build Service')
#parser.add_argument('pkg', help='PKG to build')
parser.add_argument('--syslog', action='store_true', help='Log to syslog')
parser.add_argument('-v', '--verbose', action='store_true', help='Log all traffic - including beacon')
args = parser.parse_args()


log = logging.getLogger('aurbs')
loglevel = logging.DEBUG if args.verbose else logging.INFO
log.setLevel(loglevel)
if args.syslog:
	loghandler = logging.handlers.SysLogHandler(address = '/dev/log')
else:
	loghandler = logging.StreamHandler(sys.stdout)
	formatter = logging.Formatter('[%(asctime)s] %(levelname)+8s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
	loghandler.setFormatter(formatter)
log.addHandler(loghandler)


_pkg_list = set(db.pkg_list())
_pkg_checked = set()
_remote_pkgs = db.remote_pkgs()

def remote_pkgver(name):
	return _remote_pkgs[name]

def version_newer(old, new):
	return parse_version(new) > parse_version(old)

def filter_dependencies(args, local=True, nofilter=False):
	deps = set()
	for arg in args:
		deps = deps.union(arg)
	if nofilter:
		return deps
	if local:
		return filter(lambda d: d in _pkg_list, deps)
	else:
		return filter(lambda d: d not in _pkg_list, deps)

def make_pkg(pkgname):
	pkg = db.get(pkgname)
	deps = {}
	for dep in filter_dependencies([pkg.depends, pkg.makedepends], nofilter=True):
		try:
			deps[dep] = remote_pkgver(dep)
		except KeyError:
			try:
				deps[dep] = db.get_build(dep).version
			except:
				log.error("Build: Dependency '%s' for '%s' not found!" % (dep, pkgname))
	db.set_build(pkgname, deps)
	log.warning("BUILDING PKG: %s (%s)" % (pkgname, deps))

def check_pkg(pkgname):
	if pkgname in _pkg_checked:
		return False

	do_build = False
	pkg_aur = aur.get(pkgname)
	try:
		pkg_local = db.get(pkgname)
	except:
		log.warning("AUR-PKG '%s' not found in local db --> syncing" % pkgname)
		do_build = True
		aur.sync(pkgname)
		db.import_pkg(pkgname)
		pkg_local = db.get(pkgname)
		
	if not do_build:
		if version_newer(pkg_local.version, pkg_aur.version):
			log.warning("AUR-PKG '%s' outdated in local db --> resyncing" % pkgname)
			do_build = True
			aur.sync(pkgname)
			db.import_pkg(pkgname)
			pkg_local = db.get(pkgname)
		else:
			remote_deps = filter_dependencies([pkg_local.depends], local=False)
			for dep in remote_deps:
				try:
					ver_remote = remote_pkgver(dep)
				except KeyError:
					log.error("Check: Dependency '%s' for '%s' not found!" % (dep, pkgname))
				try:
					build = db.get_build(pkgname)
					ver_local = build.linkdepends[dep]
					if version_newer(ver_local, ver_remote):
						log.warning("Remote Dependency '%s' of AUR-PKG '%s' updated (%s -> %s) --> rebuilding" % (dep, pkgname, ver_local, ver_remote))
						do_build = True
				except:
					log.warning("No build for AUR-PKG '%s' --> building" % pkgname)
					do_build = True
					break

	local_deps = filter_dependencies([pkg_local.depends, pkg_local.makedepends], local=True)
	log.debug("Inquiring local pkg '%s' - ldeps: (%s)" % (pkgname, ', '.join(local_deps)))
	for dep in local_deps:
		if check_pkg(dep):
			log.warning("Local Dependency '%s' of AUR-PKG '%s' updated --> rebuilding" % (dep, pkgname))
			do_build = True

	_pkg_checked.add(pkgname)

	if do_build:
		make_pkg(pkgname)
		return True
	else:
		return False

#check_pkg(args.pkg)

for pkg in _pkg_list:
	check_pkg(pkg)