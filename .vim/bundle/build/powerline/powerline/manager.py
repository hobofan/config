# powerline.manager - Management interface
# (c) 2008 Pianohacker, licensed under the GPLv3

import cherrypy
from powerline import web, user_error
from powerline.database import user_model, settings_model, system_model, session_model, hours_model, connect
from datetime import datetime

class user_controller(web.controller):
	@web.accessible_by('/')
	@web.expose(template = 'manager/users.html')
	def index(self): 
		"""/manager/users/ - User management"""
		return {}

	@web.accessible_by('/', 'POST')
	@web.expose(template = 'manager/users.html')
	def create(self, username):
		"""/manager/users/ - User management.

		POST - Creates a user (username parameter).
		"""
		database = connect()
		user = user_model(database)

		if user.exists(username):
			raise user_error('User %s already exists' % username)

		user.create(username)
		raise cherrypy.HTTPRedirect('/manager/users/')

	@web.accessible_by('/:user_id')
	@web.expose(template = 'manager/user.html')
	def get(self, user_id, **kwargs):
		"""/manager/users/<user_id> - Manage a particular user.

		GET - Returns details on a user.
		"""

		database = connect()
		user = user_model(database)

		if user.exists(user_id):
			return {'result': user.get(user_id)}
		else:
			raise cherrypy.NotFound()

	@web.accessible_by('/:user_id', 'POST')
	@web.expose()
	def modify(self, user_id, **kwargs):
		"""/manager/users/<user_id> - Manage a particular user.

		POST - Modifies a user.
		"""
		database = connect()
		user = user_model(database)

		if not user.exists(user_id):
			raise cherrypy.NotFound()

		if 'barred' in kwargs:
			user.ban(user_id) if int(kwargs['barred']) else user.ban(user_id, '1970-01-01')
		elif 'ban_until' in kwargs:
			user.ban(user_id, datetime.strptime(kwargs['ban_until'], '%m/%d/%Y').strftime('%Y-%m-%d'))

		raise cherrypy.HTTPRedirect('/manager/users/' + user_id)

	@web.accessible_by('/:user_id', 'DELETE')
	@web.expose()
	def delete(self, user_id):
		"""/manager/users/<user_id> - Manage a particular user.

		DELETE - Deletes a user.
		"""
		database = connect()
		user = user_model(database)

		user.delete(user_id)

		raise cherrypy.HTTPRedirect('/manager/users/')

	@web.expose(template = 'manager/user-search.html')
	def search(self, query=''):
		"""/manager/users/search - Search names of users.

		Takes a single argument of `query`, which is searched for anywhere in the username of a user.
		"""
		database = connect()
		user = user_model(database)

		yield 'query', query
		yield 'result', user.select('username LIKE %s', '%' + query + '%')

class settings_controller(web.controller):
	@web.accessible_by('/')
	@web.expose(template = 'manager/settings.html')
	def index(self):
		"""/manager/settings/ - Manage settings"""
		database = connect()
		settings = settings_model(database)

		yield 'result', dict(settings)

	@web.accessible_by('/', 'POST')
	@web.expose()
	def modify(self, key = '', value = '', **kwargs):
		"""Takes arguments `key`, `value`, and creates or modifies setting `name` accordingly"""
		database = connect()
		settings = settings_model(database)

		if key and key in settings:
			settings[key] = value
		else:
			for key, value in kwargs.items(): settings[key] = value

		raise cherrypy.HTTPRedirect('/manager/settings/')

class hours_controller(web.controller):
	@web.accessible_by('/')
	@web.expose(template = 'manager/hours.html')
	def index(self, **kwargs):
		"""/manager/hours/ - Manage hours.

		GET - Returns current hours.
		POST - Modifies hours, based on arguments of the form <weekday>_(open|close)time, e.g., 0_opentime or 6_closetime.
		"""
		database = connect()
		hours = hours_model(database)

		return hours.all()

	@web.accessible_by('/', 'POST')
	def modify(self, **kwargs):
		database = connect()
		hours = hours_model(database)
		current_hours = hours.all()

		for i in xrange(7):
			sent_properties = dict((key[2:], value) for key, value in kwargs.items() if key.startswith(str(i)))
			if sent_properties != {}:
				current_hours[i] = (datetime.strptime(sent_properties['opentime'], '%I:%M %p').time(), datetime.strptime(sent_properties['closetime'], '%I:%M %p').time())

		hours.update(current_hours)

		raise cherrypy.HTTPRedirect('/manager/hours/')

class system_controller(web.controller):
	"""Systems management"""
	@web.accessible_by("/")
	@web.expose(template = 'manager/systems.html')
	def index(self):
		"""/manager/systems/ - Manage systems.

		GET - Returns all systems.
		"""
		database = connect()
		system = system_model(database)

		return system.all()

	@web.accessible_by('/', 'POST')
	def create(self, name, title):
		"""/manager/systems/ - Manage systems.

		POST - Takes an argument of name and title, and creates a system with those properties.
		"""
		database = connect()
		system = system_model(database)

		if not title:
			raise user_error('Systems must be given a title')

		if not system.exists(name):
			system.create(name = name, title = title)

		raise cherrypy.HTTPRedirect('/manager/systems/')
	
	@web.accessible_by('/:name', 'POST')
	def modify(self, name, title):
		"""/manager/systems/<system> - Manage a particular system.

		POST - Takes an argument of name and title, and creates a system with those properties.
		"""
		database = connect()
		system = system_model(database)

		if not title:
			raise user_error('Systems must be given a title')

		if system.exists(name):
			system.update(name, title = title)

		raise cherrypy.HTTPRedirect('/manager/systems/')

	@web.accessible_by('/:name', 'DELETE')
	def delete(self, name):
		"""/manager/systems/<system> - Manage a particular system.

		DELETE - Deletes the system.
		"""
		database = connect()
		system = system_model(database)

		if system.exists(name):
			system.delete(name)
	
		raise cherrypy.HTTPRedirect('/manager/systems/')

class interface(web.controller):
	def __init__(self):
		self.users = user_controller()
		self.settings = settings_controller()
		self.systems = system_controller()
		self.hours = hours_controller()

		self._cp_config = {
			'tools.require_login.on': True
		}

		super(interface, self).__init__()

	@web.expose(template = 'manager/index.html')
	def index(self):
		"""/manager/ - Main manager page"""
		return {}
	
	@web.accessible_by('/login_setup')
	@web.expose(template = 'manager/login-setup.html')
	def login_setup(self):
		"""/manager/login_setup - Set up the manager username and password.
		
		GET - Returns current username.
		POST - Modifies username and/or password, based on arguments.
		"""
		database = connect()
		settings = settings_model(database)

		yield 'username', settings['manager_users'][0].split(':')[0]
	
	@web.accessible_by('/login_setup', 'POST')
	@web.expose(template = 'manager/login-setup.html')
	def change_login(self, username = '', password = '', confirm_password = ''):
		database = connect()
		settings = settings_model(database)

		yield 'username', settings['manager_users'][0].split(':')[0]

		assert(username and password)
		if password != confirm_password:
			raise user_error('Passwords do not match')

		settings['manager_users'] = username + ':' + password

		raise cherrypy.HTTPRedirect('/manager/')

	@web.accessible_by('/session_log')
	@web.expose(template = 'manager/session-log.html')
	def session_log(self):
		"""/manager/session_log - A log of sessions for the day.
		
		GET - Return the list of sessions.
		"""
		database = connect()
		session = session_model(database)

		return session.select('date(timestamp) = current_date ORDER BY daily_id')

	@web.accessible_by('/session_log', 'DELETE')
	def delete_session(self, session_id):
		"""/manager/session_log - A log of sessions for the day.
		
		DELETE - Delete a session.
		"""
		database = connect()
		session = session_model(database)

		session_id = int(session_id)
		assert(session.exists(session_id = session_id))
		session.delete(session_id)

		raise cherrypy.HTTPRedirect('/manager/session_log')
	
	@web.accessible_by('/login')
	@web.expose(template = 'manager/login.html')
	def login_page(self, original_page = '/manager/'):
		"""/manager/login - Log in to the manager.

		GET - Returns the login page.
		"""

		yield 'original_page', original_page

	@web.accessible_by('/login', 'POST')
	@web.expose(template = 'manager/login.html')
	def login(self, username, password, original_page = '/manager/'):
		"""/manager/login - Log in to the manager.

		POST - Checks username and password, and redirects to `original_page` if successful.
		"""
		database = connect()
		settings = settings_model(database)

		yield 'original_page', original_page

		if username + ':' + password in settings['manager_users']:
			cherrypy.session['logged-in'] = 'yes'
			yield 'destination', original_page
		else:
			raise user_error('Username or password incorrect')
	
	@cherrypy.expose
	def logout(self):
		"""/manager/logout - Log out from the manager"""
		if cherrypy.session.get('logged-in', False):
			del cherrypy.session['logged-in']

		raise cherrypy.HTTPRedirect('/')
	
	login._cp_config, login_page._cp_config = [{'tools.require_login.on': False}] * 2

	@web.expose(template = 'manager/statistics.html')
	def statistics(self):
		"""/manager/statistics - Returns statistics on sessions and users"""
		database = connect()
		session = session_model(database)
		user = user_model(database)

		return {
			'result': {
				 'sessions_for_day': session.rows('date(timestamp) = current_date').select_value('count(end_time)'),
				 'sessions_for_week': session.rows('week(timestamp) = week(current_date)').select_value('count(end_time)'),
				 'sessions_for_month': session.rows('month(timestamp) = month(current_date)').select_value('count(end_time)'),
				 'sessions_for_year': session.rows('year(timestamp) = year(current_date)').select_value('count(end_time)'),
				 'sessions': session.rows('1').select_value('count(end_time)'),
				 'registered_users': user.rows('1').select_value('count(*)'),
			}
		}
