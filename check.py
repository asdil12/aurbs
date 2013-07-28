#!/usr/bin/python2

import sys
import os
import shutil
import subprocess
from pkg_resources import parse_version

import logging
import logging.handlers
import argparse


import aur
import db
from webserver import WebServer


chroot = '/root/chroot'


parser = argparse.ArgumentParser(description='AUR Build Service')
#parser.add_argument('pkg', help='PKG to build')
parser.add_argument('--syslog', action='store_true', help='Log to syslog')
parser.add_argument('-v', '--verbose', action='store_true', help='Log all traffic - including beacon')
args = parser.parse_args()


log = logging.getLogger('aurbs')
loglevel = logging.DEBUG if args.verbose else logging.INFO
log.setLevel(loglevel)
if args.syslog:
	loghandler = logging.handlers.SysLogHandler(address = '/dev/log')
else:
	loghandler = logging.StreamHandler(sys.stdout)
	formatter = logging.Formatter('[%(asctime)s] %(levelname)+8s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
	loghandler.setFormatter(formatter)
log.addHandler(loghandler)


pkg_list = set(db.pkg_list())
pkg_checked = {}

webserver = WebServer('aurstaging', 8024)

subprocess.call(["arch-nspawn", os.path.join(chroot, 'root'), "pacman", "-Syu", "--noconfirm"])
remote_pkgs = db.remote_pkgs(os.path.join(chroot, 'root'))

def remote_pkgver(name):
	return remote_pkgs[name]

def version_newer(old, new):
	return parse_version(new) > parse_version(old)

def filter_dependencies(args, local=True, nofilter=False):
	deps = set()
	for arg in args:
		deps = deps.union(arg)
	if nofilter:
		return deps
	if local:
		return filter(lambda d: d in pkg_list, deps)
	else:
		return filter(lambda d: d not in pkg_list, deps)

def publish_pkg(pkgname, version):
	arch = 'x86_64'
	filename = '%s-%s-%s.pkg.tar.xz' % (pkgname, version, arch)
	repodir = os.path.join('aurstaging', arch)
	for item in os.listdir(repodir):
		print item
		if item.endswith('pkg.tar.xz'):
			[ipkgname, ipkgver, ipkgrel, iarch] = item.rsplit("-", 3)
			if ipkgname == pkgname:
				log.debug("Removing '%s' from repo db" % ipkgname)
				subprocess.call(['repo-remove', 'aurstaging.db.tar.gz', ipkgname], cwd=repodir)
				os.remove(item)
	shutil.copyfile(os.path.join('build', pkgname, filename), os.path.join(repodir, filename))
	log.debug("Adding '%s' to repo db" % item)
	subprocess.call(['repo-add', 'aurstaging.db.tar.gz', filename], cwd=repodir)

def make_pkg(pkgname):
	pkg = db.get(pkgname)
	deps = {}
	for dep in filter_dependencies([pkg.depends, pkg.makedepends], nofilter=True):
		try:
			deps[dep] = remote_pkgver(dep)
		except KeyError:
			try:
				deps[dep] = db.get_build(dep).version
			except:
				log.error("Build: Dependency '%s' for '%s' not found!" % (dep, pkgname))
	log.warning("BUILDING PKG: %s (%s)" % (pkgname, deps))

	subprocess.call(['bsdtar', 'xvf', os.path.join('..', 'cache', '%s.tar.gz' % pkgname)], cwd='build')
	subprocess.call(["arch-nspawn", os.path.join(chroot, 'root'), "pacman", "-Sy", "--noconfirm"])
	subprocess.call(['makechrootpkg', '-cu', '-l', 'build', '-r', chroot], cwd=os.path.join('build', pkgname))
	publish_pkg(pkgname, pkg.version)
	db.set_build(pkgname, deps)
	log.warning("DONE BUILDING PKG: %s" % (pkgname))

def check_pkg(pkgname):
	if pkgname in pkg_checked:
		return pkg_checked[pkgname]

	do_build = False
	pkg_aur = aur.get(pkgname)
	try:
		pkg_local = db.get(pkgname)
	except:
		log.warning("AUR-PKG '%s' not found in local db --> syncing" % pkgname)
		do_build = True
		aur.sync(pkgname)
		db.import_pkg(pkgname)
		pkg_local = db.get(pkgname)
		
	if not do_build:
		if version_newer(pkg_local.version, pkg_aur.version):
			log.warning("AUR-PKG '%s' outdated in local db --> resyncing" % pkgname)
			do_build = True
			aur.sync(pkgname)
			db.import_pkg(pkgname)
			pkg_local = db.get(pkgname)
		else:
			remote_deps = filter_dependencies([pkg_local.depends], local=False)
			for dep in remote_deps:
				try:
					ver_remote = remote_pkgver(dep)
				except KeyError:
					log.error("Check: Dependency '%s' for '%s' not found!" % (dep, pkgname))
				try:
					build = db.get_build(pkgname)
					ver_local = build.linkdepends[dep]
					if version_newer(ver_local, ver_remote):
						log.warning("Remote Dependency '%s' of AUR-PKG '%s' updated (%s -> %s) --> rebuilding" % (dep, pkgname, ver_local, ver_remote))
						do_build = True
				except:
					log.warning("No build for AUR-PKG '%s' --> building" % pkgname)
					do_build = True
					break

	local_deps = filter_dependencies([pkg_local.depends, pkg_local.makedepends], local=True)
	log.debug("Inquiring local pkg '%s' - ldeps: (%s)" % (pkgname, ', '.join(local_deps)))
	for dep in local_deps:
		if check_pkg(dep):
			log.warning("Local Dependency '%s' of AUR-PKG '%s' updated --> rebuilding" % (dep, pkgname))
			do_build = True

	if do_build:
		make_pkg(pkgname)
		pkg_checked[pkgname] = True
		return True
	else:
		pkg_checked[pkgname] = False
		return False

#check_pkg(args.pkg)

# create chroot:
#  pacman -S devtools
#  mkdir ~/chroot
#  CHROOT=$HOME/chroot
#  mkarchroot $CHROOT/root base-devel

# at build
# cd build ; tar xvf ../cache/pkg.tar.gz
# sudo makechrootpkg -cu -l build -r $CHROOT
# delete old pkg in repo
#   repo-remove repo.db.tar.gz pkgname-*
#   rm pkgname-*
#   cp pkg -> repo
#   repo-add repo.db.tar.gz pkgname-pkgvar-pkgrel.tar.xz


try:
	for pkg in pkg_list:
		check_pkg(pkg)
finally:
	webserver.stop()
