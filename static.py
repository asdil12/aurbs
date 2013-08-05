#!/usr/bin/env python

import os

cachedir = '/var/cache/pacman/pkg/'
srcpkgdir = '/var/cache/aurbs/srcpkgs/'
pkg_db_dir = '/var/lib/aurbs/pkg_db'

def chroot(arch):
	return os.path.join('/var/lib/aurbs/chroot', arch)

def chroot_root(arch):
	return os.path.join(chroot(arch), 'root')

def build_dir(arch):
	return os.path.join('/var/cache/aurbs/build', arch)

def ccache_dir(arch):
	return os.path.join('/var/cache/aurbs/ccache', arch)

def repodir(arch):
	return os.path.join('/var/lib/aurbs/aurstaging', arch)

def build_db_dir(arch):
	return os.path.join('/var/lib/aurbs/build_db', arch)
