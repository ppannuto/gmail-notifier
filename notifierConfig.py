import os
import gtk
import logging
import threading
import ConfigParser
from gmailLib import GmailConn

class NotifierConfigWindow:

	def __init__(self, config, gConns, gConns_lock):
		self.close_event = threading.Event ()
		self.config = config
		self.gConns = gConns
		self.gConns_lock = gConns_lock
		self.buildWindow ()
		print "Result: " + str ( self.window.run () )

		self.config.config.write (open (os.path.expanduser ('~/.gmail-notifier.conf'), 'w'))
		self.window.destroy ()
		self.close_event.set ()

	def buildWindow(self):
		# Set up the top-level window
		self.window = gtk.Dialog ()
		self.window.set_title ('GMail Notifier Preferences')
		self.window.set_position (gtk.WIN_POS_CENTER)

		# Add a vbox to hold the window contents
		self.window_vbox = self.window.get_content_area ()

		# Add instructions (Label) at the top of the window
		self.top_label = gtk.Label ('Add, remove, and configure GMail accounts')
		self.top_label.set_alignment(xalign=0.5, yalign=0.5)
		self.window_vbox.pack_start (self.top_label)
		self.top_label.show ()

		# Create widgets for each email account and pack them into the table
		self.accounts = list()
		for username in self.config.get_usernames ():
			print 'adding widgets for ' + username
			frame = gtk.Frame (username)
			bbox = gtk.HButtonBox ()
			configure = gtk.Button (stock=gtk.STOCK_PREFERENCES)
			delete = gtk.Button (stock=gtk.STOCK_DELETE)
			self.accounts.append (  (frame, bbox, configure, delete)  )

			frame.set_border_width (10)
			frame.add (bbox)
			bbox.set_border_width (5)

			bbox.set_layout (gtk.BUTTONBOX_END)
			bbox.add (configure)
			configure.connect ('clicked', self.configureAccount, username)
			bbox.add (delete)
			delete.connect ('clicked', self.deleteAccount, username)

			self.window_vbox.pack_start (frame)

			frame.show ()
			bbox.show ()
			configure.show ()
			delete.show ()

		# 'Add new account' button
		self.new_account_button = gtk.Button (stock=gtk.STOCK_ADD, label="_Add a new account...")
		self.new_account_button.set_label ('_Add a new account...')
		self.new_account_button.connect ('clicked', self.configureAccount)
		alignment = gtk.Alignment (xalign=1.0)
		alignment.add (self.new_account_button)
		self.window_vbox.pack_start (alignment)
		alignment.show ()
		self.new_account_button.show ()

		# Close window button
		#self.close_button = gtk.Button (stock=gtk.STOCK_CLOSE)
		#self.window_vbox.pack_start (self.close_button)
		#self.close_button.show ()

		self.close_event.clear ()
		self.window.show_all ()

	def configureAccount(self, widget, username=None):
		self.window.hide ()
		with self.gConns_lock:
			if username:
				print ('configureAccount with username ' + username + ' called')
				for gConn in self.gConns:
					if gConn.getUsername () == username:
						gConn.configure (self.config)
			else:
				print ('configureAccount with username=None called')
				try:
					self.gConns.append (GmailConn (config=self.config))
				except GmailConn.CancelledError:
					print ('configureAccount new account creation cancelled')
		self.buildWindow ()
		print ('configureAccount complete')
		self.window.show ()


	def deleteAccount(self, widget, username):
		self.config.config.remove_section (username)


class NotifierConfig:
	"""A configuration object for gmail-notifier. The constructor takes a list of config files."""

	class Error(Exception):
		pass

	def __init__(self, files):
		self.readConfigFiles (files)

	def readConfigFiles(self, files):
		self.config = ConfigParser.SafeConfigParser ()
		self.config.read (files)

	def showConfigWindow(self, gConns, gConns_lock):
		print 'a'
		gtk.gdk.threads_enter ()
		print 'd'
		n = NotifierConfigWindow (self, gConns, gConns_lock)
		print 'e'
		gtk.gdk.threads_leave ()
		print 'f'
		n.close_event.wait ()
		print 'g'

	def get_usernames(self):
		return self.config.sections ()

	def get_password(self, username):
		return self.config.get (username, 'password')

	def get_proxy(self, username):
		return self.config.get (username, 'proxy')

	def get_ac_polling(self, username):
		return self.config.getint (username, 'ac_polling')

	def get_battery_polling(self, username):
		return self.config.getint (username, 'battery_polling')
