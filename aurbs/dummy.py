#!/usr/bin/python

from aurbs import model
from aurbs.config import AurBSConfig

def aurpkg(pkgname):
	pkg = {
		'_id': None,
		'name': pkgname,
		'description': 'n/a',
		'license': 'n/a',
		'votes': 'n/a',
		'maintainer': 'n/a',
		'version': 'n/a',
		'arch': AurBSConfig().architectures,
		'depends': [],
		'makedepends': [],
		'srcpkg': 'https://aur.archlinux.org/packages/%s/%s/%s.tar.gz' % (pkgname[0:2], pkgname, pkgname),
		'results': {},
		'dummy': True,
		# ...
	}
	return pkg
	
