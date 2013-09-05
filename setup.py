#!/usr/bin/env python

from distutils.core import setup

setup(
	name='aurbs',
	version='0.8.3',
	license='GPL',
	description='Automatic AUR package building system',
	author='Dominik Heidler',
	author_email='dheidler@gmail.com',
	url='http://github.com/asdil12/aurbs',
	requires=['flask', 'flup'],
	packages=['aurbs', 'aurbs.ui'],
	scripts=['bin/aurbs'],
	data_files=[
		('/etc', ['templates/aurbs.yml']),
		('/usr/share/doc/aurbs', ['templates/lighttpd.conf.sample']),
	],
)
