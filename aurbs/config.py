#!/usr/bin/env python

from yaml import load, dump
try:
	from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
	from yaml import Loader, Dumper

from aurbs.model import Singleton

@Singleton
class AurBSConfig(object):
	def __init__(self, configfile):
		self.configfile = configfile
		ctxt = open(configfile, 'r').read()
		# who said, I couldn't use tabs in yaml?
		ctxt = ctxt.replace("\t", " ")
		self.config = load(ctxt, Loader=Loader)

	def __getattr__(self, key):
		return self.config[key]

	def __getitem__(self, key):
		return self.config[key]
