#!/usr/bin/python2

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

	# something went wrong (result=blocked or failed)
	blocked = 2

class FatalError(Exception):
	pass
