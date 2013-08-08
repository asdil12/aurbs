#!/usr/bin/env python

import tarfile
import os
import logging
import datetime
import shutil
import re
from pymongo import MongoClient

from aurbs import aur
from aurbs import dummy
from aurbs import pkg_parser
from aurbs.config import AurBSConfig
from aurbs.model import *
from aurbs.static import *
from aurbs.helper import *

log = logging.getLogger('aurbs')

@Singleton
class Database(object):
	def __init__(self):
		self._client = MongoClient(AurBSConfig().database['host'], AurBSConfig().database['port'])
		self._db = self._client[AurBSConfig().database['database']]
		self._db.packages.ensure_index("name", unique=True, dropDups=True)

	def get_pkg(self, pkgname):
		pkg = self._db.packages.find_one({"name": pkgname})
		if pkg:
			return pkg
		else:
			raise KeyError("Package '%s' not found in database" % pkgname)

	def sync_pkg(self, pkgname):
		aur.sync(pkgname)
		tar = tarfile.open(os.path.join(srcpkgdir, '%s.tar.gz' % pkgname))
		pkgbuild = pkg_parser.parseFile(tar.extractfile('%s/PKGBUILD' % pkgname))
		pkg = aur.get_pkg(pkgname)
		try:
			pkg['depends'] = clean_dep_ver(pkgbuild['depends'])
		except KeyError:
			pkg['depends'] = []
		try:
			pkg['makedepends'] = clean_dep_ver(pkgbuild['makedepends'])
		except KeyError:
			pkg['makedepends'] = []
		pkg['arch'] = pkgbuild['arch']
		if not self._db.packages.update({"name": pkgname}, {"$set": pkg})['n']:
			self._db.packages.insert(pkg)

	def _cleanup_results(self, pkgname):
		# cleanup non-matching results (any-results for i686-x86_64 pkg)
		pkg = self.get_pkg(pkgname)
		any_arch = True if pkg['arch'][0] == "any" else False
		for arch, result in pkg.get("results", {}).items():
			if any_arch and arch == 'any':
				continue
			elif not any_arch and arch != 'any':
				continue
			for rtype, ref in result:
				self._db["%ss" % rtype].remove(ref)
				self._db.packages.update({"_id": pkg['_id']}, {"$unset": {"results.%s" % arch: {}}})
				# also cleanup logfiles

	def set_result(self, pkgname, build_arch, rtype, **kwargs):
		# arch via pkg from db
		# rtype = problem | build
		pkg = self.get_pkg(pkgname)
		try:
			arch = "any" if pkg['arch'][0] == "any" else build_arch
			self._cleanup_results(pkgname)
		except KeyError:
			arch = build_arch
		setk = "results.%s.%s" % (arch, rtype)
		setv = {
			"name": pkg['name'],
			"arch": arch,
			"build_arch": build_arch,
			"date": datetime.datetime.utcnow(),
			"pkg": pkg['_id']
		}
		if rtype == 'build':
			setv.update({
				"linkdepends": kwargs['linkdepends'],
				"version": pkg['version']
			})
		elif rtype == 'problem':
			setv.update({
				"type": kwargs['ptype']
			})
			if kwargs['ptype'] in ['blocked_depends', 'missing_depends']:
				setv.update({
					"depends": kwargs['depends']
				})
			elif kwargs['ptype'] == 'fail':
				setv.update({
					"linkdepends": kwargs['linkdepends'],
					"version": pkg['version']
				})
		try:
			setr = pkg['results'][arch][rtype]
			assert self._db["%ss" % rtype].update({"_id": setr}, setv)['n']
		except (KeyError, AssertionError):
			setr = self._db["%ss" % rtype].insert(setv)
		self._db.packages.update({"_id": pkg['_id']}, {"$set": {setk: setr}})

	def get_result(self, pkgname, build_arch, rtype=None):
		# arch via pkg from db
		# rtype = problem | build
		pkg = self.get_pkg(pkgname)
		try:
			arch = "any" if pkg['arch'][0] == "any" else build_arch
		except KeyError:
			arch = build_arch
		if not rtype:
			describe_rtype = True
			for rtype in ['problem', 'build']:
				if pkg['results'][arch].get(rtype, None):
					break
		else:
			describe_rtype = False
		if rtype:
			rvalue = self._db["%ss" % rtype].find_one(pkg['results'][arch][rtype])
			if describe_rtype:
				return {"rtype": rtype, "rvalue": rvalue}
			else:
				return rvalue
		else:
			return None

	def get_results(self, rtype, **query):
		return self._db["%ss" % rtype].find(query)

	def delete_result(self, pkgname, build_arch, rtype):
		# arch via pkg from db
		# rtype = problem | build
		try:
			pkg = self.get_pkg(pkgname)
			try:
				arch = "any" if pkg['arch'][0] == "any" else build_arch
				self._cleanup_results(pkgname)
			except KeyError:
				arch = build_arch
			setr = pkg['results'][arch][rtype]
			self._db["%ss" % rtype].remove(setr)
			setk = "results.%s.%s" % (arch, rtype)
			self._db.packages.update({"_id": pkg['_id']}, {"$unset": {setk: None}})
		except KeyError:
			pass

	def get_pkg_required_by(self, pkgname):
		pkgs = []
		for pkg in AurBSConfig().aurpkgs:
			try:
				pkg = self.get_pkg(pkg)
				if pkgname in pkg['depends']:
					pkgs.append(pkg['name'])
			except KeyError:
				pass
		return pkgs
