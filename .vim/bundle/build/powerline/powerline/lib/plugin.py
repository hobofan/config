from os import path, listdir
from cherrypy import log
import imp

class mount_point(type):
	known = set()

	def __init__(cls, name, bases, attrs):
		if hasattr(cls, '_plugins'):
			cls.add(cls)
		else:
			cls._plugins = set()
			if 'add' not in attrs:
				cls.add = classmethod(lambda cls, plugin: cls.plugins.add(plugin))
				cls.plugins = cls._plugins

			mount_point.known.add(cls)

def load(*paths):
	for path in paths:
		load_path(path)

def load_path(location):
	for file in set([path.splitext(x)[0] for x in listdir(location) if not x.startswith('.')]):
		load_file(location, file)

def load_file(location, filename):
	found = []

	mod_name = path.splitext(filename)[0]
	new_mod = None

	try:
		fp, pathname, desc = imp.find_module(mod_name,[location])
		try:
			new_mod = imp.load_module(mod_name, fp, pathname, desc)
		finally:
			if fp: fp.close()
	except ImportError, err:
		log('Failed to import %s, %s' % (mod_name, err))

