#!/usr/bin/env python

import os
import pyalpm
from pycman.config import PacmanConfig

class RemoteDB(object):
	def __init__(self, root='/'):
		self.root = root
		pc = PacmanConfig(conf=self._rp('/etc/pacman.conf'))
		# Add root path prefix, as alpm seems to expect absolute paths
		for option in ['RootDir', 'DBPath', 'GPGDir', 'LogFile']:
			pc.options[option] = self._rp(pc.options[option])
		self.handle = pc.initialize_alpm()

	def _rp(self, path):
		"""
		Add the root prefix to a path
		"""
		return os.path.join(self.root, path.lstrip('/'))

	def get_pkg(self, pkgname):
		"""
		Get a pkg, which provides pkgname
		"""
		dbs = self.handle.get_syncdbs()
		for db in dbs:
			pkg = pyalpm.find_satisfier(db.pkgcache, pkgname)
			if pkg is not None:
				return pkg
