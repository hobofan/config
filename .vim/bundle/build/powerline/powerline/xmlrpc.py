# powerline.xmlrpc - Pre-book XML-RPC API
# (c) 2008 Pianohacker, licensed under the GPLv3

"""An implementation of the Pre-book XML-RPC API.

All Pre-book API methods take a single params argument, a dict, and return a dict.
While the system_api_procs.tcl file has five real methods, only four are actually used:
	* pcres.authenticate,
	* pcres.startsession,
	* pcres.infoupdate,
	* and pcres.closesession.

TODO: Consider a rewrite of the client and this API. The current model is ripe for abuse, and could deal with a bit of digest-authentication, or even something RESTful.
"""

import cherrypy
from cherrypy.lib import xmlrpc as _xmlrpc
from powerline import user_error
from powerline.database import user_model, session_model, settings_model, system_model, hours_model, connect
from dbwrap import bag
import datetime

from xmlrpclib import Fault

class xmlrpc_controller(object):
    # This is custom because some part of the client-xmlrpclib chain puts in spurious spaces. Evilbadhorrible people
    # Note we're hard-coding this into the 'tools' namespace. We could do
    # a huge amount of work to make it relocatable, but the only reason why
    # would be if someone actually disabled the default_toolbox. Meh.
    _cp_config = {'tools.xmlrpc.on': True}
    
    def __call__(self, *vpath, **params):
        rpcparams, rpcmethod = _xmlrpc.process_body()
        
        subhandler = self
        for attr in str(rpcmethod).split('.'):
            subhandler = getattr(subhandler, attr.strip(), None)
         
        if subhandler and getattr(subhandler, "exposed", False):
            body = subhandler(*(vpath + rpcparams), **params)
        
        else:
            # http://www.cherrypy.org/ticket/533
            # if a method is not found, an xmlrpclib.Fault should be returned
            # raising an exception here will do that; see
            # cherrypy.lib.xmlrpc.on_error
            raise Exception, 'method "%s" is not supported' % attr
        
        conf = cherrypy.request.toolmaps['tools'].get("xmlrpc", {})
        _xmlrpc.respond(body,
                        conf.get('encoding', 'utf-8'),
                        conf.get('allow_none', 0))
        return cherrypy.response.body
    __call__.exposed = True
    
    index = __call__


def require_params(params, *args):
	"""Checks that the keys in the params dict contain all of args."""
	if not all(key in params for key in args):
		raise Fault(-32500, 'required params not sent (did not get %s)' % ', '.join(set(args) - set(params.keys())))

class api(xmlrpc_controller):
	_cp_config = {
		'tools.trailing_slash.on': False,
		'tools.xmlrpc.on': True
	}

	def __init__(self):
		self.pcres = real_api()

class real_api(api):
	"""The pcres namespace of the API."""
	def __init__(self):
		pass

	@cherrypy.expose
	def authenticate(self, params):
		"""Authenticates the user.

		This method takes four arguments inside its params dict:
			* auth_name: This is the barcode of the user.
			* auth_token: This is the user's password, if valid. Note that the official client sends '0' when no password is entered.
			* system_id: This is the internal name of the system.
			* station_id: This is the numerical id (counting from 0) of a sub-station on one physical system. This will be 0, in most cases. NOTE: Powerline does not support sub-stations.

		It returns a dict like so:
			* status_code: a short string, indicating the success of the call.
				* "SUCCESS": The user authenticated successfully.
				* "WALKUP_BOOKTIME": Undocumented and unused.
				* "WALKUP_LEFTTIME": Same.
				* "AUTHFAILED": The authentication step failed. The user does not exist, or we couldn't contact the external source, etc.
				* "BOOKERR": The patron is already logged on.
				* "INUSEERR": Undocumented and unused. Note that Powerline uses this to mean that the user is not close enough to the head of the line.
				* "SYSERR": An internal error occured.
			* status_message: A user-readable and understandable message to correspond to an error.
			* patron_type: The patron category code, if we are using ILS authentication.
			* session_max_seconds: The maximum length of the session in seconds.
			* reservation_id: An internal id for this reservation. NOTE: Powerline has a unified model of reservations and sessions, so this will be the same as the session_id.
		"""

		require_params(params, 'auth_name', 'auth_token', 'system_id', 'station_id')

		error = lambda status_code, status_message: dict(status_code = status_code, status_message = status_message, patron_type = 'failed', session_max_seconds = 0, reservation_id = 0)

		database = connect()
		user = user_model(database)
		system = system_model(database)
		session = session_model(database)
		settings = settings_model(database)
		hours = hours_model(database)

		session_max_seconds = min(settings['session_time'] * 60, (datetime.datetime.combine(datetime.date.today(), hours.get_closing_time()) - datetime.datetime.now()).seconds)

		if not hours.open_now():
			return error('SYSERR', 'Currently closed')

		if not system.exists(params['system_id']):
			return error('SYSERR', 'System is not registered')

		try:
			user.verify(params['auth_name'])
		except user_error:
			return error('AUTHFAILED', 'You are not registered')

		if params['auth_name'] in settings['overrides']:
			# Evilbadhorrible hackery
			session.create(params['auth_name'])
			user_session = session.get(params['auth_name'])
			session.authenticate(user_session.session_id, params['system_id'])
			return dict(status_code = 'SUCCESS', status_message = '', patron_type = 'OVERRIDE', session_max_seconds = session_max_seconds, reservation_id = user_session.session_id)

		if params['auth_name'] in settings['overrides']:
			return dict(status_code = 'SUCCESS', status_message = '', patron_type = 'ADULT', session_max_seconds = session_max_seconds, reservation_id = user_session.session_id)

		user_session = None

		try:
			user_session = session.get(params['auth_name'])

			if user_session.start_time is not None:
				return error('BOOKERR', 'You are already logged on')

		except KeyError:
			return error('AUTHFAILED', 'You have not reserved')

		open_computers = system.get_open()

		if open_computers == []:
			return error('SYSERR', 'Attempt to log on when all computers are full')

		if settings['session_expire_time'] != 0:
			first_in_line = session.select_one('start_time IS NULL LIMIT 1')
			last_ended = session.select_one('end_time IS NOT NULL AND end_time + INTERVAL 10 minute > CURRENT_TIMESTAMP AND DATE(timestamp) = CURRENT_DATE ORDER BY end_time DESC LIMIT 1')

			if first_in_line and last_ended and len(session.get_unstarted()) > len(open_computers) and last_ended.end_time + datetime.timedelta(minutes = settings['session_expire_time']) < datetime.datetime.now():
				if first_in_line.user == params['auth_name']:
					return error('INUSEERR', 'Your session has expired')

				session.delete(first_in_line.session_id)

		line_position = user.get_line_position(params['auth_name'])

		if line_position >= len(open_computers):
			return error('INUSEERR', 'People are ahead of you in line')

		session.authenticate(user_session.session_id, params['system_id'])

		return dict(status_code = 'SUCCESS', status_message = '', patron_type = 'ADULT', session_max_seconds = session_max_seconds, reservation_id = user_session.session_id)

	@cherrypy.expose
	def startsession(self, params):
		"""Actually begin the session.

		While in Pre-book, this creates a session and returns it, in Powerline, it just adds a start_time to the reservation.

		This method takes two arguments in its params dict:
			* reservation_id: The previously given internal id for this reservation. See note in authenticate.
			* session_type: This appears to be similar to the User-Agent header in HTTP; e.g., the official client sends Win32Lock.
		
		It returns a dict like so:
			* status_code: Either "SUCCESS" (everything went well) or "SYSERR" (internal error).
			* session_id: An internal id for this session. In Powerline, same as the reservation_id.
		"""
		require_params(params, 'reservation_id', 'session_type')

		database = connect()
		session = session_model(database)

		result = dict(status_code = 'SUCCESS', session_id = 0, checkup_interval = 120)

		if not session.exists(session_id = params['reservation_id']):
			result['status_code'] = 'SYSERR'

			return result

		session.start(params['reservation_id'])

		result['session_id'] = params['reservation_id']

		return result

	@cherrypy.expose
	def closesession(self, params):
		"""Close the session.

		This method takes two arguments in its params dict:
		* session_id: The previously given internal id for this session.
		* session_end_code: A code giving the reason for the session end.
			* "user-logout": Manual logout before the session ended.
			* "privacy": Client logged out user because of inactivity.
			* "timeup": Normal logout at end of session.
			* "error": Client detected an error of some sort, and logged out.

		It returns a dict like so:
			* status_code: A short code indicating the success of the call.
				* "SUCCESS": Everything went well.
				* "BADSESSIONID": The session_id doesn't exist.
				* "SYSERR": An internal error occurred.
		"""
		require_params(params, 'session_id', 'session_end_code')

		database = connect()
		session = session_model(database)
		result = dict(status_code = 'SUCCESS')

		if not session.exists(session_id = params['session_id']):
			result['status_code'] = 'BADSESSIONID'

			return result

		session.end(params['session_id'])
	
		return result

	@cherrypy.expose
	def infoupdate(self, params):
		"""Get updated session info.

		This method takes one argument in its params dict:
			* session_id: The previously given internal id for this session.

		It returns a dict like so:
			* status_code: A short code indicating the success of the call.
				* "TIMEUNCHANGED": Nothing happened, session unaffected.
				* "TIMEEXTENDED": The client has been given more time.
				* "TIMEREDUCED": The client's session has been cut short.
				* "SYSERR": An internal error occurred.
			* status_message: A human-readable message for the client corresponding to the status_code, if something occurred.
			* session_remaining_seconds: Amount of time remaining in session, in seconds.

		Note that the official server software _always_ returns a dict like this:
			* status_code: "TIMEUNCHANGED"
			* status_message: "Your session time has been reduced 30 minutes by library staff"
			* session_remaining_seconds: 360

		These values do not correspond to anything in the real world, so this method can not be relied on for anything if compatibility with the official server software is required.
		"""
		require_params(params, 'session_id')

		database = connect()
		session = session_model(database)
		settings = settings_model(database)
		hours = hours_model(database)
		result = dict(status_code = 'TIMEUNCHANGED', status_message = '', session_remaining_seconds = 0)
		
		if not session.exists(session_id = params['session_id']):
			result['status_code'] = 'SYSERR'
			result['status_message'] = 'Bad session_id'
			result['session_remaining_seconds'] = 0
			
			return result

		now = datetime.datetime.now()

		user_session = session.get(session_id = params['session_id'])
		session_time = min(settings['session_time'] * 60, (datetime.datetime.combine(datetime.date.today(), hours.get_closing_time()) - datetime.datetime.now()).seconds)
		result['session_remaining_seconds'] = ((user_session.start_time + datetime.timedelta(0, session_time, 0)) - datetime.datetime.now()).seconds

		return result

	@cherrypy.expose
	def clearsession(self, params):
		"""Clear all sessions for a machine.

		This is supposed to be called when a computer reboots. Since the official client does not actually use this, implementing it is low priority.

		This method takes one argument in its params dict:
			* system_id: The internal id of the system.

		This method returns a dict like so:
			* status_code: Either "SUCCESS" (everything went well) or "SYSERR" (internal error).
		"""
		return dict(status_code = 'SUCCESS')
