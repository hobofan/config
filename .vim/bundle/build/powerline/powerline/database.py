# powerline.database - Database access
# (c) 2008 Pianohacker, licensed under the GPLv3

import dbwrap
from os import path
from powerline.lib.plugin import mount_point
from powerline import user_error
import datetime
from decimal import Decimal
import MySQLdb

user = ''
host = 'localhost'
password = ''
database = 'powerline'
charset = 'utf8'

def connect():
	"""Returns a dbwrap'd connection to the MySQL database specified in config."""
	return dbwrap.wrapper(MySQLdb.connect(user = user, host = host, passwd = password, db = database, use_unicode = True, charset = charset), placeholder = '%s')

class user_checker(object):
	__metaclass__ = mount_point

class internal_checker(user_checker, dbwrap.table_ref):
	def __init__(self, connection):
		dbwrap.table_ref.__init__(self, connection, 'users')

	def verify(self, username = None):
		"""Returns the user with `username`, and adds a key 'banned' which indicates whether the user is banned."""
		user = self.rows(username = username).select_one('*', 'allowed_after >= CURRENT_DATE AS banned')
		
		if not user:
			raise KeyError(username)

		if user.banned:
			return False, 'You are banned'
		else:
			return True, ''

	def exists(self, username):
		return self.rows(username = username).exist()

class user_model(dbwrap.table_ref):
	def __init__(self, connection):
		dbwrap.table_ref.__init__(self, connection, 'users')
		self.checkers = [checker(connection) for checker in user_checker.plugins]
	
	def create(self, username):
		self.insert(username = username)
		self.con.commit()
	
	def exists(self, username):
		return self.rows(username = username).exist()
	
	def verify(self, username):
		exists = False

		for checker in self.checkers:
			try:
				verified, message = checker.verify(username)
			except KeyError:
				continue

			exists = True

			if not verified:
				raise user_error(message)
		else:
			if not exists:
				raise user_error('User %s does not exist' % username)

	def get(self, username = None):
		"""Returns the user with `username`, and adds a key 'banned' which indicates whether the user is banned."""
		user = self.rows(username = username).select_one('*', 'allowed_after >= CURRENT_DATE AS banned')

		if not user:
			raise KeyError(user)

		return user
	
	def ban(self, username, until = datetime.date.max):
		"""Bans `username` until `until` if specified, otherwise forever."""
		self.rows(username = username).update(allowed_after = until)
		self.con.commit()
	
	def delete(self, username):
		assert(self.exists(username))

		self.rows(username = username).delete()
		self.con.commit()

	def get_line_position(self, username):
		"""Returns the position in line, counting from 1.

		If the user is already logged on, this returns -1. If they are ready to get on, it returns 0.
		"""
		session = session_model(self.con)
		system = system_model(self.con)

		try:
			reservation = session.get(username)

			if reservation.start_time != None:
				return -1
			
			for i, row in enumerate(session.get_unstarted()):
				if row.user == username:
					break
			else:
				raise user_error('fatal contradiction in get_line_position')

			return max(0, i + 1 - system.get_num_open())
		except KeyError:
			raise user_error('user does not have a reservation')
			
	__getitem__ = get


class system_model(dbwrap.table_ref):
	def __init__(self, connection):
		dbwrap.table_ref.__init__(self, connection, 'systems')
	
	def exists(self, system):
		return self.rows(name = system).exist()

	def create(self, name, title):
		self.insert(name = name, title = title)
		self.con.commit()
	
	def get(self, name):
		return self.select(name = name)

	def update(self, _name, **kwargs):
		"""Update the system `_name` to the values in kwargs."""
	 	super(system_model, self).rows(name = _name).update(**kwargs)
		self.con.commit()
	
	def delete(self, name):
		super(system_model, self).rows(name = name).delete()
		self.con.commit()
	
	def get_open(self):
		"""Returns the list of open systems."""
		return list(self.select('NOT EXISTS (SELECT session_id FROM sessions WHERE sessions.system = systems.name AND sessions.start_time IS NOT NULL AND sessions.end_time IS NULL)'))
	
	def get_num_open(self):
		"""Returns the number of open systems."""
		return self.rows('NOT EXISTS (SELECT session_id FROM sessions WHERE sessions.system = systems.name AND sessions.start_time IS NOT NULL AND sessions.end_time IS NULL)').select_value('COUNT(*)')
	
	def all_open(self):
		"""Returns whether all systems are open."""
		return len(self.all()) == self.get_num_open()

class session_model(dbwrap.table_ref):
	def __init__(self, connection):
		dbwrap.table_ref.__init__(self, connection, 'sessions')
		self.settings = settings_model(connection)
		self.users = user_model(connection)
		self.hours = hours_model(connection)
	
	def exists(self, username = None, **kwargs):
		return self.rows(**kwargs).exist() if kwargs else self.rows(user = username).exist()

	def create(self, username):
		"""Creates a session from the specified `username`."""

		# A little housekeeping...
		self.rows('date(timestamp) < current_date AND start_time IS NULL').delete()

		if not self.hours.open_now():
			raise user_error('Currently closed')

		self.users.verify(username)

		if self.rows(user = username, end_time = None).exist():
			raise user_error('You have already reserved a computer')
	
		last = self.rows('date(timestamp) = current_date').select_value('max(daily_id)')
		daily_id = 1
		if last is not None:
			daily_id = last + 1

		self.insert(user = username, daily_id = daily_id)
		self.con.commit()
	
	def delete(self, session_id):
		self.rows(session_id = session_id).delete()
		self.con.commit()

	def authenticate(self, session_id, system):
		"""Registers the specified `session_id` on `system`."""
		self.rows(session_id = session_id).update(system = system)
		self.con.commit()

	def start(self, session_id):
		"""Updates the start_time of of the session with `session_id` to the current time."""
		self.rows(session_id = session_id).update(start_time = datetime.datetime.now())
		self.con.commit()
	
	def end(self, session_id):
		"""Updates the end_time of of the session with `session_id` to the current time."""
		self.rows(session_id = session_id).update(end_time = datetime.datetime.now())
		self.con.commit()

	def get(self, username = None, **kwargs):
		"""If `username` is given, returns the first unended session for that user. Otherwise, it returns the session that matches `kwargs`."""
		results = self.select_one(**kwargs) if kwargs else self.select_one(user = username, end_time = None)

		if not results:
			raise KeyError(username or kwargs)
		else:
			return results

	__getitem__ = get

	def get_unstarted(self):
		"""Returns the list of unstarted sessions."""
		return self.select('start_time IS NULL AND date(timestamp) = current_date ORDER BY timestamp')

	def get_unended(self):
		"""Returns the list of unended sessions."""
		return self.select('end_time IS NULL AND date(timestamp) = current_date ORDER BY timestamp')

	def get_open_time(self):
		"""Returns when a system is likely to open up."""
		settings = settings_model(self.con)

		last_session = self.select_one('start_time IS NOT NULL AND end_time IS NULL ORDER BY start_time DESC LIMIT 1')
		
		if last_session:
			return last_session.start_time + datetime.timedelta(minutes = settings['session_time'])
		else:
			return datetime.datetime.now()

class settings_model(dbwrap.table_ref):
	"""A dict-like object that supports getting, setting and existence testing of settings.

	It also supports typed settings; if a setting is marked with a known type, then it is run through the function for that type.
	"""
	types = {
		'int': int,
		'float': float,
		'decimal': lambda val: Decimal(str(val)),
		'list': lambda val: [subval.strip() for subval in val.split(',')],
	}

	def __init__(self, connection):
		dbwrap.table_ref.__init__(self, connection, 'settings')
	
	def __getitem__(self, key):
		result = self.select_one(name = key)
		if result:
			if result.type in self.types:
				return self.types[result.type](result.value)
			else:
				return result.value
		else:
			raise KeyError(key)
	
	def __setitem__(self, key, value):
		if key in self:
			info = self.get_info(key)
			if info.type in self.types:
				self.types[info.type](value)

			self.rows(name = key).update(value = value)
		else:
			self.insert(name = key, value = value)

		self.con.commit()
	
	def __contains__(self, key):
		return self.rows(name = key).exist()
	
	def get_info(self, key):
		"""Returns the information for `key`, including its description and type."""
		result = self.select_one(name = key)
		
		if not result:
			raise KeyError(key)
		else:
			return result
	
	def register(self, key, value = '', type = 'none'):
		if key not in self:
			self.insert(name = key, type = type, value = value)
	
	def __iter__(self):
		return ((row.name, self[row.name]) for row in self.all())

class hours_model(object):
	"""A 'virtual' model, built on the 'hours' setting, that deals with hours."""
	def __init__(self, connection):
		self.settings = settings_model(connection)
	
	@staticmethod
	def _time_from_string(string):
		return datetime.datetime.strptime(string, '%H:%M').time()

	def all(self):
		"""Returns the hours for every day of the week, as a list of 2-tuples of datetime.time's."""
		return [tuple(self._time_from_string(time) for time in day.split('-')) for day in self.settings['hours']]
	
	def get(self, weekday = None):
		"""Returns the hours for `weekday` (specified numerically, starting from Sunday), if specified, otherwise today."""
		now = datetime.datetime.now()
		if weekday is None:
			weekday = now.date().weekday()
			weekday = 0 if weekday == 6 else weekday + 1

		return self.all()[weekday]

	def get_opening_time(self):
		"""Returns the opening time for today."""
		return self.get()[0]
	
	def get_closing_time(self):
		"""Returns the closing time for today."""
		return self.get()[1]

	def update(self, new_hours):
		"""Updates hours from `new_hours`, a list of 2-tuples of datetime.time's."""
		assert len(new_hours) == 7 and all(len(hours) == 2 and type(hours[0]) == type(hours[1]) == datetime.time for hours in new_hours)

		self.settings['hours'] = ','.join('-'.join(hour.strftime('%H:%M') for hour in hours) for hours in new_hours)
	
	def open_now(self):
		"""Returns whether we are currently open."""
		now = datetime.datetime.now().time()
		open, closing = self.get()

		return open <= now < closing
