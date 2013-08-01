#!/usr/bin/env python

import os
import subprocess
import sys

archs = ['i686', 'x86_64']

tplvars = {
	'makepkg': {
		'i686': {
			'CARCH': 'i686',
			'CHOST': 'i686-pc-linux-gnu',
			'MARCH': 'i686'
		},
		'x86_64': {
			'CARCH': 'x86_64',
			'CHOST': 'x86_64-unknown-linux-gnu',
			'MARCH': 'x86-64'
		},
	},
	'pacman': {
		'i686': {
			'ARCH': 'i686'
		},
		'x86_64': {
			'ARCH': 'x86_64'
		}
	}
}

if len(sys.argv) > 1:
	root = sys.argv[1]
else:
	root = '/'

def mkdir(path):
	path = os.path.join(root, path)
	print(path)
	try:
		os.makedirs(path)
	except OSError as e:
		if not e.errno == 17:
			raise

def chown(path, uid, gid):
	path = os.path.join(root, path)
	print("CHOWN: %s" % path)
	os.chown(path, uid, gid)

def process_template(infile, outfile, tvars):
	txt = open(os.path.join('templates', infile)).read()
	for key, value in tvars.items():
		txt = txt.replace('%%%s%%' % key, value)
	outfile = os.path.join(root, outfile)
	print(outfile)
	open(outfile, 'w').write(txt)

def dummy_repo_db(repo_path):
	repo_path = os.path.join(root, repo_path)
	print(os.path.join(repo_path, 'aurstaging.db'))
	try:
		if not os.path.exists(os.path.join(repo_path, 'aurstaging.db.tar.gz')):
			subprocess.call(['tar', 'czf', 'aurstaging.db.tar.gz', '--files-from', '/dev/null'], cwd=repo_path)
		if not os.path.exists(os.path.join(repo_path, 'aurstaging.db')):
			os.symlink('aurstaging.db.tar.gz', os.path.join(repo_path, 'aurstaging.db'))
	except OSError:
		# File exists
		pass


mkdir('usr/share/aurbs/cfg')
mkdir('var/cache/aurbs/srcpkgs')
mkdir('var/lib/aurbs/pkg_db')

for arch in archs:
	process_template('makepkg.conf.in', 'usr/share/aurbs/cfg/makepkg.conf.%s' % arch, tplvars['makepkg'][arch])
	process_template('pacman.conf.in', 'usr/share/aurbs/cfg/pacman.conf.%s' % arch, tplvars['pacman'][arch])

	mkdir('var/cache/aurbs/build/%s' % arch)

	mkdir('var/cache/aurbs/ccache/%s' % arch)
	chown('var/cache/aurbs/ccache/%s' % arch, 99, 99)

	mkdir('var/lib/aurbs/build_db/%s' % arch)
	mkdir('var/lib/aurbs/chroot/%s' % arch)

	mkdir('var/lib/aurbs/aurstaging/%s' % arch)
	dummy_repo_db('var/lib/aurbs/aurstaging/%s' % arch)
