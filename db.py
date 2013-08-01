#!/usr/bin/env python

import simplejson as json
import tarfile
import os
import logging
import time

import aur
from model import *
import pkg_parser
import re


log = logging.getLogger('aurbs')

_re_strip_ver = re.compile(r"([^<>=]*)[<>]?=?")

def _clean_dep_ver(deps):
	deps_out = []
	for dep in deps:
		deps_out.append(_re_strip_ver.match(dep).group(1))
	return deps_out

def import_pkg(pkgname):
	tar = tarfile.open('/var/cache/aurbs/srcpkgs/%s.tar.gz' % pkgname)
	pkgbuild = pkg_parser.parseFile(tar.extractfile('%s/PKGBUILD' % pkgname))
	a = aur.get(pkgname)
	try:
		a._data['depends'] = _clean_dep_ver(pkgbuild['depends'])
	except KeyError:
		a._data['depends'] = []
	try:
		a._data['makedepends'] = _clean_dep_ver(pkgbuild['makedepends'])
	except KeyError:
		a._data['makedepends'] = []
	a._data['arch'] = _clean_dep_ver(pkgbuild['arch'])
	json.dump(a._data, open('/var/lib/aurbs/pkg_db/%s.json' % pkgname, 'w'), sort_keys=True, indent=4)

def get_pkg(pkgname):
	try:
		r = json.load(open('/var/lib/aurbs/pkg_db/%s.json' % pkgname, 'r'))
		a = AurPkg(r)
		return a
	except IOError:
		raise KeyError("No such pkg: '%s'" % pkgname)

def get_build(pkgname, arch):
	try:
		b = json.load(open('/var/lib/aurbs/build_db/%s/%s.json' % (arch, pkgname), 'r'))
		b = PkgBuild(b)
		return b
	except IOError:
		raise KeyError("No such build: '%s'" % pkgname)

def set_build(pkgname, dependencies, arch):
	b = PkgBuild(get_pkg(pkgname)._data)
	b._data['linkdepends'] = dependencies
	b._data['build_time'] = int(time.time())
	json.dump(b._data, open('/var/lib/aurbs/build_db/%s/%s.json' % (arch, pkgname), 'w'), sort_keys=True, indent=4)
