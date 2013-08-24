#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango
import xmlrpclib
import sys
import time

SERVER = 'http://localhost:8080/XMLRPC'
SYSTEMS = {'computer2': '#2', 'computer3': '#3', 'computer4': '#4', 'computer5': '#5'}
proxy, pcres = None, None

class user_error(Exception):
	pass

class client(object):
	session_end_code = 'user-logout'
	client_id = 'powerline test_client'

	def __init__(self, system_id):
		self.system_id = system_id
		self.reservation = {}
		self.session = {}
	
	def login(self, barcode):
		"""Logs in as 'barcode'.

		Usage: client.login('<barcode>')
		"""
		reservation = pcres.authenticate(dict(auth_name = barcode, auth_token = '', system_id = self.system_id, station_id = 0))
		if reservation['status_code'] != 'SUCCESS':
			raise user_error('%s in pcres.authenticate: %s' % (reservation['status_code'], reservation['status_message']))

		self.reservation = reservation

		session = pcres.startsession(dict(reservation_id = reservation['reservation_id'], session_type = self.client_id))
		if session['status_code'] != 'SUCCESS':
			raise user_error('%s in pcres.startsession: %s' % (session['status_code'], session['status_message']))

		self.session = session
	
	def update(self):
		"""Get updated session info.

		Usage: client.update()
		"""
		if not self.session:
			raise user_error('login first')

		return pcres.infoupdate(dict(session_id = self.session['session_id']))

	def logout(self):
		"""Logs out.

		Usage: client.logout()
		"""
		if not self.session:
			raise user_error('login first')

		result = pcres.closesession(dict(session_id = self.session['session_id'], session_end_code = self.session_end_code))
		if result['status_code'] != 'SUCCESS':
			raise user_error('%s in pcres.closesession' % result['status_code'])

class client_widget(gtk.VBox, client):
	def __init__(self, system_id):
		client.__init__(self, system_id)
		gtk.VBox.__init__(self, spacing = 20)
	
		self.status = gtk.Label('Please enter your barcode')
		status_attrs = pango.AttrList()
		status_attrs.insert(pango.AttrSize(12*1000, 0, 1000))
		self.status.set_attributes(status_attrs)
		self.pack_start(self.status)

		self.entry_box = gtk.HBox()
		self.pack_start(self.entry_box, expand = False)

		self.barcode_entry = gtk.Entry()
		self.barcode_entry.connect('activate', self.run_login)
		self.entry_box.pack_start(self.barcode_entry)

		self.barcode_submit = gtk.Button('Log in')
		self.barcode_submit.connect('clicked', self.run_login)
		self.entry_box.pack_start(self.barcode_submit)

		self.logout_button = gtk.Button('Log out')
		self.logout_button.set_no_show_all(True)
		self.logout_button.connect('clicked', self.run_logout)
		self.pack_start(self.logout_button, expand = False)

		self.show_all()

		self.session_time = 0
		self.updater = None
	
	def run_login(self, widget):
		try:
			self.login(self.barcode_entry.get_text())
		except user_error, e:
			dialog = gtk.MessageDialog(type = gtk.MESSAGE_ERROR, buttons = gtk.BUTTONS_OK, message_format = e.message)

			dialog.run(); dialog.destroy()

			return

		self.entry_box.hide()
		self.logout_button.show()

		self.session_time = int(self.reservation['session_max_seconds'])

		self.status.set_text('Logged in for %d minutes and %d seconds' % (
			self.session_time // 60,
			self.session_time % 60
		))

		self.updater = gobject.timeout_add(1000, self.run_update)

	def run_logout(self, widget):
		self.logout()

		self.status.set_text('Please enter your barcode')
		self.barcode_entry.set_text('')
		self.entry_box.show()
		self.logout_button.hide()

		gobject.source_remove(self.updater)
		self.session_time = 0
	
	def run_update(self):
		self.session_time -= 1

		if self.session_time == 0:
			self.run_logout()
			return False

		self.status.set_text('Logged in for %d minutes and %d seconds' % (
			self.session_time // 60,
			self.session_time % 60
		))

		return True

class client_window(gtk.Window):
	def destroy(self, widget, data=None):
		gtk.main_quit()

	def __init__(self):
		# create a new window
		gtk.Window.__init__(self)
	
		self.connect("destroy", self.destroy)
	
		self.container = gtk.Notebook()
		self.clients = []

		for id, title in SYSTEMS.items():
			client = client_widget(id)
			label = gtk.Label(title)
			label.set_padding(15, 0)
			self.clients.append(client)
			self.container.append_page(client, label)

		self.container.connect('switch-page', self.update_title)
		self.container.homogeneous = True
		self.add(self.container)

		self.set_default_size(400, 200)
		self.set_title('Powerline client - ' + SYSTEMS.itervalues().next())
		self.show_all()
	
	def update_title(self, notebook, page, page_num):
		title = self.container.get_tab_label_text(self.container.get_nth_page(page_num))

		self.set_title('Powerline client - ' + title)
		
def inputloop():
	my_client = client(sys.argv[1])

	while True:
		try:
			barcode = raw_input('Barcode > ')

			my_client.login(barcode)
			print 'Logged in for', '%d minutes and %d seconds' % (my_client.reservation['session_max_seconds'] // 60, my_client.reservation['session_max_seconds'] % 60), 'hit Ctrl-C to log out'
			while True:
				try:
					time.sleep(60)
					result = my_client.update()
					if result['status_code'] != 'TIMEUNCHANGED': print 'Session status: ', result['status_message']
					print 'Time left: ', '%d minutes and %d seconds' % (result['session_remaining_seconds'] // 60, result['session_remaining_seconds'] % 60)
				except KeyboardInterrupt:
					my_client.logout()
					break
		except user_error, e:
			print 'Error: ' + e.message
		except KeyboardInterrupt:
			return
		except:
			sys.__excepthook__(*sys.exc_info())

if __name__ == '__main__':
	if '--gtk' in sys.argv:
		if not 2 <= len(sys.argv) <= 3:
			print 'Usage: python -m powerline.tools.client [host]'
			print 'NOTE: host defaults to ' + SERVER
			raise SystemExit(1)

		if len(sys.argv) == 3:
			SERVER = sys.argv[2]

		proxy = xmlrpclib.ServerProxy(SERVER)
		pcres = proxy.pcres

		main = client_window()
		try:
			gtk.main()
		finally:
			for client in main.clients:
				if client.session:
					try:
						client.logout()
					except:
						pass
	else:
		if not 2 <= len(sys.argv) <= 3:
			print 'Usage: python -m powerline.tools.client <system id> [host]'
			print 'NOTE: host defaults to ' + SERVER
			raise SystemExit(1)

		if len(sys.argv) == 3:
			SERVER = sys.argv[2]

		proxy = xmlrpclib.ServerProxy(SERVER)
		pcres = proxy.pcres

		print 'Powerline test client'
		inputloop()
