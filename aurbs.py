#!/usr/bin/env python

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
from config import AurBSConfig
from webserver import WebServer
from remotedb import RemoteDB


parser = argparse.ArgumentParser(description='AUR Build Service')
#parser.add_argument('pkg', help='PKG to build')
parser.add_argument('--syslog', action='store_true', help='Log to syslog')
parser.add_argument('-c', '--config', default='/etc/aurbs.yml', help='Set log to DEBUG')
parser.add_argument('-v', '--verbose', action='store_true', help='Set log to DEBUG')
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


def remote_pkgver(name):
	try:
		return remote_db.get_pkg(name).version
	except AttributeError:
		raise KeyError("No provider found for remote pkg '%s'" % name)

def version_newer(old, new):
	return parse_version(new) > parse_version(old)

def filter_dependencies(args, local=True, nofilter=False):
	deps = set()
	for arg in args:
		deps = deps.union(arg)
	if nofilter:
		return deps
	if local:
		return [d for d in deps if d in AurBSConfig().aurpkgs]
	else:
		return [d for d in deps if d not in AurBSConfig().aurpkgs]

def publish_pkg(pkgname, version, arch):
	filename = '%s-%s-%s.pkg.tar.xz' % (pkgname, version, arch)
	cachedir = '/var/cache/pacman/pkg/'

	for item in os.listdir(repodir):
		print(item)
		if item.endswith('pkg.tar.xz'):
			[ipkgname, ipkgver, ipkgrel, iarch] = item.rsplit("-", 3)
			if ipkgname == pkgname:
				log.debug("Removing '%s' from repo db" % ipkgname)
				try:
					subprocess.call(['repo-remove', 'aurstaging.db.tar.gz', ipkgname], cwd=repodir)
				except OSError:
					pass
				os.remove(os.path.join(repodir, item))

	# Prevent old pkg being cached
	if os.path.isfile(os.path.join(cachedir, filename)):
		os.remove(os.path.join(cachedir, filename))

	shutil.copyfile(os.path.join(build_dir, pkgname, filename), os.path.join(repodir, filename))
	log.debug("Adding '%s' to repo db" % item)
	subprocess.call(['repo-add', 'aurstaging.db.tar.gz', filename], cwd=repodir)

def make_pkg(pkgname, arch):
	pkg = db.get_pkg(pkgname)
	deps = {}
	for dep in filter_dependencies([pkg.depends, pkg.makedepends], local=False):
		try:
			deps[dep] = {'version': remote_pkgver(dep)}
		except KeyError:
			log.error("Build: Dependency '%s' for '%s' not found!" % (dep, pkgname))
	for dep in filter_dependencies([pkg.depends, pkg.makedepends], local=True):
		try:
			dep_build = db.get_build(dep, arch)
			deps[dep] = {'version': dep_build.version, 'build_time': dep_build.build_time}
		except KeyError:
			log.error("Build: Dependency '%s' for '%s' not found!" % (dep, pkgname))
	log.warning("BUILDING PKG: %s (%s)" % (pkgname, deps))

	build_dir_pkg = os.path.join(build_dir, pkgname)

	# Create the directory to prevent pkgs exploiting other pkgs (tarbombs)
	try:
		os.mkdir(build_dir_pkg)
	except FileExistsError:
		pass
	subprocess.check_call(['bsdtar', '--strip-components', '1', '-xvf', os.path.join('/var/cache/aurbs/srcpkgs', '%s.tar.gz' % pkgname)], cwd=build_dir_pkg)

	# Hack to fix bad pkgs having 600/700 dependencies
	os.chmod(build_dir_pkg, 0o755)
	for r, ds, fs in os.walk(build_dir_pkg):
		for d in ds:
			os.chmod(os.path.join(r, d), 0o755)
		for f in fs:
			os.chmod(os.path.join(r, f), 0o644)

	subprocess.check_call(['makechrootpkg', '-cu', '-l', 'build', '-r', chroot, '--', '--noprogressbar'], cwd=build_dir_pkg)
	arch_publish = 'any' if pkg.arch[0] == 'any' else arch
	publish_pkg(pkgname, pkg.version, arch_publish)
	db.set_build(pkgname, deps, arch)
	log.warning("DONE BUILDING PKG: %s" % (pkgname))

def check_pkg(pkgname, arch):
	if pkgname in pkg_checked:
		return pkg_checked[pkgname]

	do_build = False

	pkg_aur = aur.get(pkgname)

	# Check PKG in local db & up to date
	try:
		try:
			pkg_local = db.get_pkg(pkgname)
		except:
			log.warning("AUR-PKG '%s' not found in local db --> syncing" % pkgname)
			raise
		if version_newer(pkg_local.version, pkg_aur.version):
			log.warning("AUR-PKG '%s' outdated in local db --> resyncing" % pkgname)
			raise
	except:
		aur.sync(pkgname)
		db.import_pkg(pkgname)
		pkg_local = db.get_pkg(pkgname)

	# Check against previous build
	try:
		pkg_build = db.get_build(pkgname, arch)

		# Check version changed
		if version_newer(pkg_build.version, pkg_local.version):
			log.warning("AUR-PKG '%s' outdated build --> rebuilding" % pkgname)
			do_build = True
		else:
			# Check for remote dependency updates
			remote_deps = filter_dependencies([pkg_local.depends], local=False)
			for dep in remote_deps:
				try:
					ver_remote = remote_pkgver(dep)
					ver_local = pkg_build.linkdepends[dep]['version']
					if version_newer(ver_local, ver_remote):
						log.warning("Remote Dependency '%s' of AUR-PKG '%s' updated (%s -> %s) --> rebuilding" % (dep, pkgname, ver_local, ver_remote))
						do_build = True
						break
				except KeyError:
					log.error("Check: Dependency '%s' for '%s' not found!" % (dep, pkgname))
	except Exception as e:
		log.warning("No build for AUR-PKG '%s' --> building" % pkgname)
		print("EXCEPTION-FIXME: %s" % e)
		do_build = True

	# Check for local dependencs updates
	local_deps = filter_dependencies([pkg_local.depends, pkg_local.makedepends], local=True)
	log.debug("Inquiring local pkg '%s' - ldeps: (%s)" % (pkgname, ', '.join(local_deps)))
	for dep in local_deps:
		# Rebuild trigger
		if check_pkg(dep, arch):
			log.warning("Local Dependency '%s' of AUR-PKG '%s' rebuilt --> rebuilding" % (dep, pkgname))
			do_build = True
		# New dependency build available
		elif not do_build:
			dep_build_time_link = pkg_build.linkdepends[dep]['build_time']
			dep_build_time_available = db.get_build(dep, arch).build_time
			if dep_build_time_link < dep_build_time_available:
				log.warning("Local Dependency '%s' of AUR-PKG '%s' updated --> rebuilding" % (dep, pkgname))
				do_build = True

	if do_build:
		make_pkg(pkgname, arch)
		pkg_checked[pkgname] = True
		return True
	else:
		pkg_checked[pkgname] = False
		return False


# Initialize config
log.debug("Reading config from '%s'" % args.config)
AurBSConfig(args.config)

webserver = WebServer('/var/lib/aurbs/aurstaging', 8024)

try:
	for arch in AurBSConfig().architectures:
		log.info("Building for architecture %s" % arch)
		chroot = os.path.join('/var/lib/aurbs/chroot', arch)
		chroot_root = os.path.join(chroot, 'root')
		build_dir = os.path.join('/var/cache/aurbs/build', arch)
		repodir = os.path.join('/var/lib/aurbs/aurstaging', arch)

		# Create chroot, if missing
		if not os.path.exists(chroot_root):
			subprocess.call(['mkarchroot',
				'-C', '/usr/share/aurbs/cfg/pacman.conf.%s' % arch,
				'-M', '/usr/share/aurbs/cfg/makepkg.conf.%s' % arch,
				chroot_root,
				'base-devel', 'ccache', 'git'
			])

		subprocess.call(["arch-nspawn", chroot_root, "pacman", "-Syu", "--noconfirm", "--noprogressbar"])
		remote_db = RemoteDB(chroot_root)
		pkg_checked = {}
		for pkg in AurBSConfig().aurpkgs:
			check_pkg(pkg, arch)
		#TODO: Publish repo
finally:
	webserver.stop()
