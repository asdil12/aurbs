#!/usr/bin/python

import tarfile
import os
import logging
import datetime
import shutil
import re
from pymongo import MongoClient

from aurbs import aur
from aurbs import dummy
from aurbs import aurinfo
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
		if AurBSConfig().database.get('user'):
			try:
				self._db.authenticate(AurBSConfig().database['user'], AurBSConfig().database['pass'])
				log.info("Authentificated with database user '%s'" % AurBSConfig().database['user'])
			except Exception as e:
				print(e)
				raise FatalError("Authentification failed with database user '%s'" % AurBSConfig().database['user'])
		else:
			try:
				self._db.collection_names()
			except Exception:
				raise FatalError("Database requires authentification")
		self._db.packages.ensure_index("name", unique=True, dropDups=True)
		for rtype in ['build', 'problem']:
			self._db["%ss" % rtype].ensure_index("name")

	def get_pkg(self, pkgname):
		pkg = self._db.packages.find_one({"name": pkgname})
		if pkg:
			return pkg
		else:
			raise KeyError("Package '%s' not found in database" % pkgname)

	def get_pkgbase(self, pkgname):
		pkg = self._db.packages.find_one({"splitpkgs": pkgname})
		if pkg:
			return pkg
		else:
			raise KeyError("Package '%s' not found in database" % pkgname)

	def get_provider(self, pkgname):
		pkg = self._db.packages.find_one({"provides": pkgname})
		if pkg:
			return pkg
		else:
			raise KeyError("Package '%s' not found in database" % pkgname)

	def get_all_provides(self):
		provides = []
		for pkg in self._db.packages.find({}):
			provides.extend(pkg['provides'])
		return set(provides)

	def sync_pkg(self, pkgname):
		# download the src pkg
		aur.sync(pkgname)

		# get some info via api
		pkg = aur.get_pkg(pkgname)

		# parse the .SRCINFO/.AURINFO file from the src pkg
		# using https://github.com/falconindy/pkgbuild-introspection/blob/master/test/aurinfo.py
		tar = tarfile.open(os.path.join(srcpkgdir, '%s.tar.gz' % pkgname))
		if '%s/.AURINFO' % pkg['pkgbase'] in tar.getnames():
			srcinfo = tar.extractfile('%s/.AURINFO' % pkg['pkgbase'])
		elif '%s/.SRCINFO' % pkg['pkgbase'] in tar.getnames():
			srcinfo = tar.extractfile('%s/.SRCINFO' % pkg['pkgbase'])
		else:
			# legacy mode: ancent pkg withoud .SRCINFO/.AURINFO
			# --> need to parse PKGBUILD
			log.info("Falling back to legacy PKGBUILD parser for pkg '%s'" % pkgname)
			pkgbuild = pkg_parser.parseFile(tar.extractfile('%s/PKGBUILD' % pkg['pkgbase']))
			#FIXME: legacy mode fails because there are no pkg['provides'] and pkg['splitpkgs']

		try:
			srcinfo = srcinfo.read().decode("UTF-8").split("\n")
			srcinfo = aurinfo.ParseAurinfoFromIterable(srcinfo, AurInfoEcatcher(pkgname, log))
			# handle splitpkgs
			pkg['splitpkgs'] = list(srcinfo.GetPackageNames())
			pkg['provides'] = list(srcinfo.GetPackageNames())
			srcinfo = [srcinfo.GetMergedPackage(splitpkg) for splitpkg in pkg['provides']]
		except NameError:
			srcinfo = [pkgbuild]

		pkg['arch'] = srcinfo[0]['arch']
		pkg['depends'] = []
		pkg['makedepends'] = []

		for splitpkg in srcinfo:
			pkg['depends'].extend(clean_dep_ver(splitpkg.get('depends', [])))
			pkg['makedepends'].extend(clean_dep_ver(splitpkg.get('makedepends', [])))
			pkg['provides'].extend(clean_dep_ver(splitpkg.get('provides', [])))

		# drop duplicate entries
		pkg['depends'] = list(set(pkg['depends']))
		pkg['makedepends'] = list(set(pkg['makedepends']))
		pkg['provides'] = list(set(pkg['provides']))

		# filter loop deps pointing to provides of this pkg
		pkg['depends'] = list(filter(lambda d: d not in pkg['provides'], pkg['depends']))
		pkg['makedepends'] = list(filter(lambda d: d not in pkg['provides'], pkg['makedepends']))

		if not self._db.packages.update({"name": pkgname}, {"$set": pkg})['n']:
			self._db.packages.insert(pkg)

	def update_pkg(self, pkgname, pkg):
		self._db.packages.update({"name": pkgname}, {"$set": pkg})

	def _cleanup_results(self, pkgname):
		# cleanup non-matching results (any-results for i686-x86_64 pkg)
		try:
			pkg = self.get_pkg(pkgname)
			any_arch = True if pkg['arch'][0] == "any" else False
			for rtype in ['build', 'problem']:
				for result in self._db["%ss" % rtype].find({'name': pkgname}):
					if any_arch and result['arch'] == 'any':
						continue
					elif not any_arch and result['arch'] != 'any':
						continue
					self._db["%ss" % rtype].remove({'_id': result['_id']})
		except KeyError:
			pass

	def set_result(self, pkgname, build_arch, rtype, **kwargs):
		# arch via pkg from db
		# rtype = problem | build
		self._cleanup_results(pkgname)
		try:
			pkg = self.get_pkg(pkgname)
			arch = "any" if pkg['arch'][0] == "any" else build_arch
		except KeyError:
			pkg = dummy.aurpkg(pkgname)
			arch = build_arch
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
				"release": kwargs['release'],
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
			setr = self.get_result(pkgname, build_arch=build_arch, rtype=rtype)
			self._db["%ss" % rtype].update({'_id': setr['_id']}, setv)
		except KeyError:
			setr = self._db["%ss" % rtype].insert(setv)

	def get_result(self, pkgname, build_arch=None, arch=None, rtype=None):
		# rtype = problem | build
		if not arch:
			try:
				pkg = self.get_pkg(pkgname)
				# arch via pkg from db
				arch = "any" if pkg['arch'][0] == "any" else build_arch
			except KeyError:
				arch = build_arch
		if rtype:
			rvalue = self._db["%ss" % rtype].find_one({'name': pkgname, 'arch': arch})
			if not rvalue:
				raise KeyError("No %s result for %s-%s" % (rtype, pkgname, arch))
			return rvalue
		else:
			for rtype in ['problem', 'build']:
				rvalue = self._db["%ss" % rtype].find_one({'name': pkgname, 'arch': arch})
				if rvalue:
					return {"rtype": rtype, "rvalue": rvalue}
			return None

	def get_results(self, rtype, **query):
		return self._db["%ss" % rtype].find(query)

	def delete_result(self, pkgname, build_arch, rtype):
		# arch via pkg from db
		# rtype = problem | build
		self._cleanup_results(pkgname)
		try:
			pkg = self.get_pkg(pkgname)
			arch = "any" if pkg['arch'][0] == "any" else build_arch
		except KeyError:
			arch = build_arch
		rvalue = self._db["%ss" % rtype].find_one({'name': pkgname, 'arch': arch})
		if rvalue:
			self._db["%ss" % rtype].remove({'_id': rvalue['_id']})

	def set_status(self, scheduled, done, arch, building=None):
		count = len(scheduled) + len(done)
		count += 1 if building else 0
		status = {
			"type": "status",
			"scheduled": scheduled,
			"done": done,
			"building": building,
			"arch": arch,
			"count": count
		}
		try:
			sid = self._db.info.find_one({'type': 'status'})['_id']
			self._db.info.update({'_id': sid}, status)
		except Exception:
			self._db.info.insert(status)

	def get_status(self):
		status = self._db.info.find_one({'type': 'status'})
		status.pop("_id")
		return status

	def get_pkg_required_by(self, pkgname):
		provides = set(self.get_pkg(pkgname)['provides'])
		pkgs = []
		for pkg in AurBSConfig().aurpkgs:
			try:
				pkg = self.get_pkg(pkg)
				if provides.intersection(pkg['depends']):
					pkgs.append(pkg['name'])
			except KeyError:
				pass
		return pkgs

	def cleanup_orphaned(self):
		# cleanup pkgs and results, that are not in AurBSConfig().aurpkgs
		for pkg in self._db.packages.find({}):
			if pkg['name'] not in AurBSConfig().aurpkgs:
				self._db.packages.remove({'name': pkg['name']})
				log.info("Cleanup orphaned db pkg-entry: %s" % pkg['name'])
		for rtype in ['build', 'problem']:
			for result in self.get_results(rtype):
				if result['name'] not in AurBSConfig().aurpkgs:
					self._db["%ss" % rtype].remove({'name': result['name']})
					log.info("Cleanup orphaned db result-entry: %s" % result['name'])

	def filter_dependencies(self, args, local=True, nofilter=False):
		deps = set()
		for arg in args:
			deps = deps.union(arg)
		if nofilter:
			return deps
		pkgs = set(AurBSConfig().aurpkgs)
		pkgs = pkgs.union(self.get_all_provides())
		if local:
			return [d for d in deps if d in pkgs]
		else:
			return [d for d in deps if d not in pkgs]
