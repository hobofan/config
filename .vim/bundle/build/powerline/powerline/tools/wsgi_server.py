#!/usr/bin/python
# powerline.tools.wsgi_server
# This is a script for mod_wsgi.

CONFIGURATION_FILES = ['/opt/powerline/etc/powerline.conf']

if __name__ == '__main__':
	import sys
	sys.stdout = sys.stderr

	import atexit
	import cherrypy

	from powerline.main import root

	for config_file in CONFIGURATION_FILES:
		cherrypy.config.update(config_file)

	cherrypy.config.update({'environment': 'embedded'})

	if cherrypy.engine.state == 0:
		cherrypy.engine.start(blocking=False)
		atexit.register(cherrypy.engine.stop)

	application = cherrypy.Application(root(), None)
