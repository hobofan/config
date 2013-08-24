# powerline.web - Web tools
# (c) 2008 Pianohacker, licensed under the GPLv3

"""Web tools.

Functions
=========
expose is a decorator that replaces CherryPy's @expose and the x.exposed = True idiom. It renders output to a template, and performs JSON serialization of results and errors.

Configuration Globals
=====================

template_dir (web.template_dir): Where the templates are loaded from.
"""

from functools import wraps
import types
from os import path
from genshi.template.loader import TemplateLoader
from powerline import json as jsonlib, user_error
import cherrypy
import posixpath as urlpath
import routes
import sys

template_dir = ''

def accessible_by(route, method = 'GET', **kwargs):
	def decorator(func):
		kwargs.update({'handler': func.__name__})
		kwargs.setdefault('conditions', {})['method'] = method
		func._route = route, kwargs
		return func

	return decorator

class controller(object):
	def __init__(self):
		self.mapper = routes.Mapper(explicit = True)

		for attr in type(self).__dict__.values():
			if hasattr(attr, '_route'):
				self.mapper.connect(attr._route[0], **attr._route[1])
				attr.exposed = False

		self.mapper.create_regs()
	
	@cherrypy.expose
	def default(self, *args, **kwargs):
		self.mapper.environ = cherrypy.request.wsgi_environ.copy()
		self.mapper.environ['REQUEST_METHOD'] = kwargs.pop('method', cherrypy.request.method)

		match = self.mapper.match('/' + (urlpath.join(*args) if args else ''))

		if not match:
			raise cherrypy.NotFound()

		handler_func = getattr(self, match['handler'])
		del match['handler']
		kwargs.update(match)
	
		return handler_func(**kwargs)

def expose(template = None, method = 'xhtml', **render_kwargs):
	"""A decorator that renders the return value of its wrapped function in a template, or serializes it to a template..

	Templates are loaded from the templates directory in the directory of the module.

	The return value of the function is transformed into a variables dict for the template in the following ways:
		* If the function is a generator, it is expected to yield 'key', 'value' tuples to be fed into dict().
		* If the value is a string, it is used unmodified.
		* If the value is a dict, it is used verbatim.
		* Anything else is an error.
		* If 'destination' is in the result dict, a redirect is fired with that value.
		* `method` and **render_kwargs are both passed to Genshi's render.

	If this is an XMLHttpRequest, it is serialized to JSON as follows:
		* A dict is directly serialized, with 'success': True added if not present.
		* Anything else is placed into a dict like {'result': result, 'success': True}
		* If an error occurs, it is serialized to {'success': False, 'error_type': type(e).__name__, 'error': str(e).
	"""

	def decorator(func):
		loader = None
		if not path.exists(template_dir):
			cherrypy.log('Template directory not valid')
			raise SystemExit(1)

		loader = TemplateLoader(template_dir, auto_reload = True)

		@wraps(func)
		def wrapper(*args, **kwargs):
			try: 
				try:
					body = {}
					result = func(*args, **kwargs)

					if type(result) is types.GeneratorType:
						body.update(result)
					else:
						body = result
				except user_error, e:
					body.update({
						'error_type': 'user_error',
						'error': str(e),
						'success': False,
					})

				if cherrypy.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
					cherrypy.response.headers['Content-Type'] = 'application/json'

					if isinstance(body, dict):
						if 'destination' in body:
							del body['destination']

						body.setdefault('success', True)
						return jsonlib.write(body)
					else:
						return jsonlib.write({'success': True, 'result': body})

				if not isinstance(body, (dict, basestring)):
					body = {'result': body, 'success': True}

				if isinstance(body, basestring):
					return result
				elif isinstance(body, dict):
					if 'destination' in body:
						raise cherrypy.HTTPRedirect(body['destination'])

					if template is None:
						return loader.load('dump.html').generate(result = body).render(method, **render_kwargs)
					else:
						return loader.load(template).generate(**body).render(method, **render_kwargs)
			except Exception, e:
				if cherrypy.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
					cherrypy.response.headers['Content-Type'] = 'application/json'

					if type(e) is cherrypy.HTTPRedirect:
						return jsonlib.write({'success': True})

					if isinstance(e, cherrypy.HTTPError):
						cherrypy.response.status = e.status, ''

					return jsonlib.write({'success': False, 'error_type': type(e).__name__, 'error': str(e)})
				else:
					raise

		wrapper.exposed = True

		return wrapper
	
	return decorator

def require_login(login_page = '/manager/login'):
	"""A tool that requires a logged-in session for access; `login_page` is where it redirects to."""
	if not cherrypy.session.loaded: cherrypy.session.load() # Dammit
	if not cherrypy.session.get('logged-in', False):
		raise cherrypy.HTTPRedirect(login_page + '?original_page=' + cherrypy.request.app.script_name + cherrypy.request.path_info)

cherrypy.tools.require_login = cherrypy.Tool('before_handler', require_login, priority = 99)
