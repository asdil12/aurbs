#!/usr/bin/python2

class AurPkg(dict):
	def __init__(self, data=None):
		self._data = data

	def __getattr__(self, key):
		return self._data[key]

	def __getitem__(self, key):
		return self._data[key]

	def import_aur(self, r):
		self._data = {
			"maintainer": r['Maintainer'],
			"description": r['Description'],
			"license": r['License'],
			"id": r['ID'],
			"version": r['Version'],
			"name": r['Name'],
			"srcpkg": 'https://aur.archlinux.org' + r['URLPath'],
			"votes": r['NumVotes'],
		}
	
	def __repr__(self):
		return "<AurPkg %s-%s>" % (self.name, self.version)

class PkgBuild(dict):
	def __init__(self, data=None):
		self._data = data

	def __getattr__(self, key):
		return self._data[key]

	def __getitem__(self, key):
		return self._data[key]

	def __repr__(self):
		return "<PkgBuild %s-%s>" % (self.name, self.version)

class Singleton(object):
	def __init__(self, cls):
		self.cls = cls
		self.instance = None
	def __call__(self, *args, **kwargs):
		if self.instance is None:
			self.instance = self.cls(*args, **kwargs)
		return self.instance

class Dependency(object):
	# old build is available
	ok = 0

	# new build is available
	rebuilt = 1

	# no build is available and something went wrong
	blocked = 2

class FatalError(Exception):
	pass
