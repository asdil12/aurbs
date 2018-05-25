#!/usr/bin/python

from distutils.core import setup

setup(
	name='aurbs',
	version='1.3.2',
	license='GPL',
	description='Automatic AUR package building system',
	author='Dominik Heidler',
	author_email='dominik@heidler.eu',
	url='http://github.com/asdil12/aurbs',
	requires=['flask', 'flup'],
	packages=['aurbs', 'aurbs.ui'],
	scripts=['bin/aurbs'],
	data_files=[
		('/etc', ['templates/aurbs.yml']),
		('/usr/share/aurbs/cfg', ['templates/gpg.conf']),
		('/usr/share/doc/aurbs', ['templates/lighttpd.conf.sample']),
	],
)
