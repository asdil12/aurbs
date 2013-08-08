#!/usr/bin/env python

from aurbs import model

def aurpkg(pkgname):
	pkg = {
		'name': pkgname,
		'description': 'n/a',
		'license': 'n/a',
		'votes': 'n/a',
		'maintainer': 'n/a',
		'version': 'n/a',
		'arch': ['n/a'],
		'depends': [],
		'makedepends': [],
		'srcpkg': 'https://aur.archlinux.org/packages/%s/%s/%s.tar.gz' % (pkgname[0:2], pkgname, pkgname),
		'results': {},
		# ...
	}
	return pkg
	
