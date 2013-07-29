#!/usr/bin/python2

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


def convert_provide(provide, version):
	if '=' in provide:
		(name, pversion) = provide.split('=')
		if '-' in pversion:
			return (name, pversion)
		else:
			release = version.split('-')[1]
			return (name, "%s-%s" % (pversion, release))
			
	else:
		return (provide, version)


def remote_pkgs(chroot='/'):
	log.info("Reading pacman sync repos...")
	pkgs = {}
	pkg_last = None
	for sdb in filter(lambda d: d.endswith('.db'), os.listdir(os.path.join(chroot, 'var/lib/pacman/sync/'))):
		tar = tarfile.open(os.path.join(chroot, 'var/lib/pacman/sync/', sdb))
		for m in tar.getmembers():
			if m.isdir():
				[pkgname, pkgver, pkgrel] = m.name.rsplit("-", 2)
				pkgs[pkgname] = pkgver + "-" + pkgrel
				pkg_last = pkgname
			elif m.isfile() and m.name.endswith('depends'):
				depf = [e.split('\n') for e in tar.extractfile(m.name).read().split('\n\n')]
				for group in depf:
					if group.pop(0) == '%PROVIDES%':
						for provide in group:
							[pkgname, pkgvr] = convert_provide(provide, pkgs[pkg_last])
							pkgs[pkgname] = pkgvr
	log.info("Reading pacman sync repos... DONE")
	return pkgs
				
	
def pkg_list():
	return [
		'libuhd',
		'gnuradio',
		'gr-osmosdr',
		'gqrx',
	]
