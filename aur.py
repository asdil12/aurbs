#!/usr/bin/env python

import simplejson as json
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from optparse import OptionParser

from model import *

target_url = "http://aur.archlinux.org/rpc.php"

class AppURLopener(urllib.request.FancyURLopener):
	version = 'AURJSON-Example/1.0 python'

urllib.request._urlopener = AppURLopener()

def search(args):
	params = urllib.parse.urlencode({'type':'search', 'arg':args})
	response = urllib.request.urlopen("%s?%s" % (target_url,params)).read()
	print_results(json.loads(response))

def info(args):
	params = urllib.parse.urlencode({'type':'info', 'arg':args})
	response = urllib.request.urlopen("%s?%s" % (target_url,params)).read()
	print_results(json.loads(response))

def get(pkgname, failcount=0):
	params = urllib.parse.urlencode({'type':'info', 'arg':pkgname})
	response = urllib.request.urlopen("%s?%s" % (target_url,params)).read()
	result = json.loads(response)
	if not result['resultcount'] == 1 and result['type'] == 'info':
		if failcount > 1:
			raise Exception("Invalid AUR API result for '%s'" % pkgname)
		else:
			return get(pkgname, failcount+1)
		
	r = result['results']
	a = AurPkg()
	a.import_aur(r)
	return a

def sync(pkgname):
	a = get(pkgname)
	u = urllib.request.urlopen(a.srcpkg)
	f = open("/var/cache/aurbs/srcpkgs/%s.tar.gz" % pkgname, 'wb')
	f.write(u.read())
	f.close()

def print_results(data):
	if data['type'] == 'error':
		print('Error: %s' % data['results'])
		return
	if not isinstance(data['results'], list):
		data['results'] = [data['results'],]
	print('Packages:')
	for pkg in data['results']:
		for name in pkg:
			print('  %s: %s' % (name, pkg[name]))
		print('')

def main():
	usage = "usage: %prog [options] arg"
	parser = OptionParser(usage=usage)
	parser.set_defaults(search_mode=0)
	parser.add_option("-s",
			"--search",
			action="store_const",
			const=0,
			dest="search_mode",
			help="Operate in search mode")
	parser.add_option("-i",
			"--info",
			action="store_const",
			const=1,
			dest="search_mode",
			help="Operate in detail mode")

	(options, args) = parser.parse_args()
	if len(args) < 1:
		parser.error("Incorrect number of arguments")
	if options.search_mode == 1:
		info(args[0])
	else:
		search(args[0])

if __name__ == "__main__":
	main()

