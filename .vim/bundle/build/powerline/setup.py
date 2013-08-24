#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
	name = 'powerline',
	version = '0.2.4',
	description = 'Simple computer reservations system',
	zip_safe = False,
	author = 'Pianohacker',
	author_email = 'pianohacker@gmail.com',
	license = 'GPLv3',
	url = 'http://code.google.com/p/powerline/',

	packages = find_packages(),
	include_package_data = True,
	package_data = {
		'powerline': [
			'templates/*.html',
			'templates/manager/*.html',
			'templates/data/*.js',
			'templates/data/*.css',
			'templates/data/images/*'
		]
	},
	zip_safe = False,

	install_requires = [
		'setuptools>=0.6b1',
		'Genshi>=0.4.1',
		'CherryPy>=3.0.0',
		'dbwrap>=0.1.6',
		'MySQL-python'
	],
)
