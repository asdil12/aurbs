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
