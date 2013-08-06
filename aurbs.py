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
from model import Dependency, FatalError
from static import *


parser = argparse.ArgumentParser(description='AUR Build Service')
parser.add_argument('pkg', nargs='?', help='Package to build')
parser.add_argument('--syslog', action='store_true', help='Log to syslog')
parser.add_argument('-c', '--config', default='/etc/aurbs.yml', help='Set alternative config file')
parser.add_argument('-v', '--verbose', action='store_true', help='Set log to DEBUG')
parser.add_argument('-s', '--strict', action='store_true', help='Exit on build failures')
parser.add_argument('-f', '--force', action='store_true', help='Force rebuild')
parser.add_argument('-F', '--forceall', action='store_true', help='Force rebuild also dependencies')
parser.add_argument('-a', '--arch', help='Set build architecture')
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

def find_pkg_files(pkgname, directory):
	respkgs = []
	for item in os.listdir(directory):
		if item.endswith('pkg.tar.xz'):
			[ipkgname, ipkgver, ipkgrel, iarch] = item.rsplit("-", 3)
			if ipkgname == pkgname:
				respkgs.append(item)
	return respkgs

def publish_pkg(pkgname, arch, version, arch_publish):
	filename = '%s-%s-%s.pkg.tar.xz' % (pkgname, version, arch_publish)
	repo_archs = AurBSConfig().architectures if arch_publish == 'any' else [arch]

	# Delete old file from repo and repodb
	for repo_arch in repo_archs:
		for item in find_pkg_files(pkgname, repodir(repo_arch)):
			[ipkgname, ipkgver, ipkgrel, iarch] = item.rsplit("-", 3)
			log.debug("Removing '%s' from %s repo db" % (ipkgname, repo_arch))
			try:
				subprocess.call(['repo-remove', 'aurstaging.db.tar.gz', ipkgname], cwd=repodir(repo_arch))
			except OSError:
				pass
			os.remove(os.path.join(repodir(repo_arch), item))
	for item in find_pkg_files(pkgname, repodir('any')):
		os.remove(os.path.join(repodir('any'), item))

	# Prevent old pkg being cached
	if os.path.isfile(os.path.join(cachedir, filename)):
		os.remove(os.path.join(cachedir, filename))

	shutil.copyfile(os.path.join(build_dir(arch), pkgname, filename), os.path.join(repodir(arch_publish), filename))
	for repo_arch in repo_archs:
		if arch_publish == 'any':
			os.symlink(os.path.join('..', arch_publish, filename), os.path.join(repodir(repo_arch), filename))
		log.debug("Adding '%s' to %s repo db" % (filename, repo_arch))
		subprocess.check_call(['repo-add', 'aurstaging.db.tar.gz', filename], cwd=repodir(repo_arch))

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

	build_dir_pkg = os.path.join(build_dir(arch), pkgname)
	src_pkg = os.path.join('/var/cache/aurbs/srcpkgs', '%s.tar.gz' % pkgname)

	# Create the directory to prevent pkgs exploiting other pkgs (tarbombs)
	try:
		os.mkdir(build_dir_pkg)
	except FileExistsError:
		for filename in find_pkg_files(pkgname, build_dir_pkg):
			os.remove(os.path.join(build_dir_pkg, filename))
		for filename in os.listdir(build_dir_pkg):
			if filename.endswith('.log'):
				os.remove(os.path.join(build_dir_pkg, filename))
	subprocess.check_call(['bsdtar', '--strip-components', '1', '-xvf', src_pkg], cwd=build_dir_pkg)

	# Hack to fix bad pkgs having 600/700 dependencies
	os.chmod(build_dir_pkg, 0o755)
	for r, ds, fs in os.walk(build_dir_pkg):
		for d in ds:
			os.chmod(os.path.join(r, d), 0o755)
		for f in fs:
			os.chmod(os.path.join(r, f), 0o644)

	arch_publish = 'any' if pkg.arch[0] == 'any' else arch
	try:
		subprocess.check_call(['makechrootpkg', '-cu', '-l', 'build', '-C', ccache_dir(arch), '-r', chroot(arch), '--', '--noprogressbar'], cwd=build_dir_pkg)
		for item in find_pkg_files(pkgname, build_dir_pkg):
			[ipkgname, ipkgver, ipkgrel, iarch] = item.rsplit("-", 3)
			log.info("Publishing pkg '%s'" % item)
			ver_publish = '%s-%s' % (ipkgver, ipkgrel)
			publish_pkg(pkgname, arch, ver_publish, arch_publish)
			# Cleanup built pkg
			os.remove(os.path.join(build_dir_pkg, item))
		db.set_build(pkgname, deps, arch, arch_publish)
		db.unset_fail(pkgname, arch_publish)
		log.warning("Done building '%s'" % pkgname)
		return True
	except Exception as e:
		log.error("Failed building '%s'" % pkgname)
		log.warning("Error: %s" % e)
		db.set_fail(pkgname, deps, arch, arch_publish)
		if args.strict:
			raise FatalError('Build Failure')
		return False

def check_pkg(pkgname, arch, do_build=False):
	if pkgname in pkg_checked:
		return pkg_checked[pkgname]

	build_blocked = False
	build_available = True

	#FIXME: also handle Exceptions via FatalError
	# and see if args.strict is set
	pkg_aur = aur.get(pkgname)

	# Check PKG in local db & up to date
	try:
		try:
			pkg_local = db.get_pkg(pkgname)
			src_pkg = os.path.join('/var/cache/aurbs/srcpkgs', '%s.tar.gz' % pkgname)
			if not os.path.exists(src_pkg):
				log.warning("AUR-PKG '%s' src-pkg not found --> syncing" % pkgname)
				raise
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
				except KeyError:
					log.error("Check: Dependency '%s' for '%s' not found! Build blocked." % (dep, pkgname))
					build_blocked = True
				try:
					ver_local = pkg_build.linkdepends[dep]['version']
					if version_newer(ver_local, ver_remote):
						log.warning("Remote Dependency '%s' of AUR-PKG '%s' updated (%s -> %s) --> rebuilding" % (dep, pkgname, ver_local, ver_remote))
						do_build = True
						break
				except KeyError:
					# This only happens if a packager added a dependency
					# without increasing the pkgrel
					log.warning("Remote Dependency '%s' of AUR-PKG '%s' added (%s) --> rebuilding" % (dep, pkgname, ver_remote))
					do_build = True
					break
	except Exception as e:
		log.warning("No build for AUR-PKG '%s' --> building" % pkgname)
		build_available = False
		do_build = True
		print("EXCEPTION-FIXME: %s" % e)

	# Check for local dependencs updates
	local_deps = filter_dependencies([pkg_local.depends, pkg_local.makedepends], local=True)
	log.debug("Inquiring local pkg '%s' - ldeps: (%s)" % (pkgname, ', '.join(local_deps)))
	for dep in local_deps:
		# Rebuild trigger
		dep_res = check_pkg(dep, arch, args.forceall)
		if dep_res == Dependency.rebuilt:
			log.warning("Local Dependency '%s' of AUR-PKG '%s' rebuilt --> rebuilding" % (dep, pkgname))
			do_build = True
		elif dep_res == Dependency.blocked:
			build_blocked = True
		# New dependency build available
		# any pkg's are not rebuilt, as this would lead to building them still for each arch
		elif not do_build and not pkg_local.arch[0] == 'any':
			dep_build_time_link = pkg_build.linkdepends[dep]['build_time']
			dep_build_time_available = db.get_build(dep, arch).build_time
			if dep_build_time_link < dep_build_time_available:
				log.warning("Local Dependency '%s' of AUR-PKG '%s' updated --> rebuilding" % (dep, pkgname))
				do_build = True

	if not build_blocked:
		if do_build:
			if make_pkg(pkgname, arch):
				pkg_checked[pkgname] = Dependency.rebuilt
			elif not build_available:
				pkg_checked[pkgname] = Dependency.blocked
		else:
			pkg_checked[pkgname] = Dependency.ok
	else:
		pkg_checked[pkgname] = Dependency.ok if build_available else Dependency.blocked
	return pkg_checked[pkgname]


# Initialize config
log.debug("Reading config from '%s'" % args.config)
AurBSConfig(args.config)

webserver = WebServer('/var/lib/aurbs/aurstaging', 8024)

try:
	for arch in AurBSConfig().architectures if not args.arch else [args.arch]:
		log.info("Building for architecture %s" % arch)

		# Create chroot, if missing
		if not os.path.exists(chroot_root(arch)):
			subprocess.check_call(['mkarchroot',
				'-C', '/usr/share/aurbs/cfg/pacman.conf.%s' % arch,
				'-M', '/usr/share/aurbs/cfg/makepkg.conf.%s' % arch,
				chroot_root(arch),
				'base-devel', 'ccache', 'git'
			])

		subprocess.check_call(["arch-nspawn", chroot_root(arch), "pacman", "-Syu", "--noconfirm", "--noprogressbar"])
		remote_db = RemoteDB(chroot_root(arch))
		pkg_checked = {}
		for pkg in AurBSConfig().aurpkgs if not args.pkg else [args.pkg]:
			check_pkg(pkg, arch, args.force or args.forceall)
			#TODO: write status page
		if not args.arch and not args.pkg:
			#TODO: Publish repo
			pass
except FatalError as e:
	log.error("Fatal Error: %s" % e)
	sys.exit(1)
finally:
	webserver.stop()
