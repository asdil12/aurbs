#!/usr/bin/env python

import simplejson as json
import tarfile
import os
import logging
import time
import shutil

import aur
from config import AurBSConfig
from model import *
from static import *
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
	tar = tarfile.open(os.path.join(srcpkgdir, '%s.tar.gz' % pkgname))
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
	json.dump(a._data, open(os.path.join(pkg_db_dir, '%s.json' % pkgname), 'w'), sort_keys=True, indent=4)

def get_pkg(pkgname):
	try:
		r = json.load(open(os.path.join(pkg_db_dir, '%s.json' % pkgname), 'r'))
		a = AurPkg(r)
		return a
	except IOError:
		raise KeyError("No such pkg: '%s'" % pkgname)

def get_build(pkgname, arch):
	try:
		b = json.load(open(os.path.join(build_db_dir(arch), '%s.json' % pkgname), 'r'))
		b = PkgBuild(b)
		return b
	except IOError:
		raise KeyError("No such build: '%s'" % pkgname)

def set_build(pkgname, dependencies, arch, arch_publish):
	b = PkgBuild(get_pkg(pkgname)._data)
	b._data['linkdepends'] = dependencies
	b._data['build_time'] = int(time.time())
	b._data['build_arch'] = arch
	build_file = os.path.join(build_db_dir(arch_publish), '%s.json' % pkgname)
	if os.path.lexists(build_file):
		os.remove(build_file)
	json.dump(b._data, open(os.path.join(build_db_dir(arch_publish), '%s.json' % pkgname), 'w'), sort_keys=True, indent=4)
	if arch_publish == 'any':
		for build_arch in AurBSConfig().architectures:
			filename = '%s.json' % pkgname
			source = os.path.join('..', arch_publish, filename)
			target = os.path.join(build_db_dir(build_arch), filename)
			if os.path.lexists(target):
				os.remove(target)
			os.symlink(source, target)

def set_fail(pkgname, dependencies, arch, arch_publish):
	fails_dir_pkg = os.path.join(fails_dir(arch_publish), pkgname)
	b = PkgBuild(get_pkg(pkgname)._data)
	b._data['linkdepends'] = dependencies
	b._data['build_time'] = int(time.time())
	b._data['build_arch'] = arch
	if os.path.lexists(fails_dir_pkg):
		if os.path.isdir(fails_dir_pkg):
			shutil.rmtree(fails_dir_pkg)
		else:
			os.remove(fails_dir_pkg)
	os.mkdir(fails_dir_pkg)
	json.dump(b._data, open(os.path.join(fails_dir_pkg, 'pkg.json'), 'w'), sort_keys=True, indent=4)
	# fetch logfiles
	build_dir_pkg = os.path.join(build_dir(arch), pkgname)
	for filename in os.listdir(build_dir_pkg):
		if filename.endswith('build.log'):
			target = 'build.log'
		elif filename.endswith('check.log'):
			target = 'check.log'
		elif filename.endswith('package.log'):
			target = 'package.log'
		else:
			continue
		shutil.copyfile(os.path.join(build_dir_pkg, filename), os.path.join(fails_dir_pkg, target))
	if arch_publish == 'any':
		for build_arch in AurBSConfig().architectures:
			source = os.path.join('..', arch_publish, pkgname)
			target = os.path.join(fails_dir(build_arch), pkgname)
			if os.path.lexists(target):
				if os.path.isdir(target):
					shutil.rmtree(target)
				else:
					os.remove(target)
			os.symlink(source, target)

def unset_fail(pkgname, arch_publish):
	fails_dir_pkg = os.path.join(fails_dir(arch_publish), pkgname)
	if os.path.lexists(fails_dir_pkg):
		if os.path.isdir(fails_dir_pkg):
			shutil.rmtree(fails_dir_pkg)
		else:
			os.remove(fails_dir_pkg)
	if arch_publish == 'any':
		for build_arch in AurBSConfig().architectures:
			target = os.path.join(fails_dir(build_arch), pkgname)
			if os.path.lexists(target):
				if os.path.isdir(target):
					shutil.rmtree(target)
				else:
					os.remove(target)
