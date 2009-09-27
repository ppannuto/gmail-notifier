import os
import gtk
import logging
import threading
import ConfigParser
from gmailLib import GmailConn
import keyring

class NotifierConfigWindow:

	def __init__(self, config, gConns, gConns_lock, onNewGConn=None, onNewGConnArgs=None, onDeleteGConn=None, onDeleteGConnArgs=None):
		self.close_event = threading.Event ()
		self.config = config
		self.gConns = gConns
		self.gConns_lock = gConns_lock
		self.onNewGConn = onNewGConn
		self.onNewGConnArgs = onNewGConnArgs
		self.onDeleteGConn = onDeleteGConn
		self.onDeleteGConnArgs = onDeleteGConnArgs
		self.buildWindow ()
		self.window.run ()
		self.window.destroy ()
		self.close_event.set ()

	def buildWindow(self):
		# Set up the top-level window
		self.window = gtk.Dialog ()
		self.window.set_title ('Preferences')
		try:
			self.window.set_icon_from_file ('nomail.png')
		except:
			pass
		self.window.set_position (gtk.WIN_POS_CENTER)
		self.window.set_default_size (250,100)

		# Add a vbox to hold the window contents
		self.window_vbox = self.window.get_content_area ()

		# Add buttons for every account
		self.accounts = self.generateAccountsFrames ()
		temp = self.accounts.keys ()
		temp.sort ()
		for username in temp:
			self.window_vbox.pack_start (self.accounts[username][0])

		# Put this button in the Dialog 'Action Area'
		self.window_bbox = self.window.get_action_area ()
		# 'Add new account' button
		self.new_account_button = gtk.Button (stock=gtk.STOCK_ADD, label="_Add a new account...")
		self.new_account_button.set_label ('_Add a new account...')
		self.new_account_button.connect ('clicked', self.configureAccount)
		self.window_bbox.add (self.new_account_button)
		self.new_account_button.show ()

		# Close window button
		#self.close_button = gtk.Button (stock=gtk.STOCK_CLOSE)
		#self.window_vbox.pack_start (self.close_button)
		#self.close_button.show ()

		self.close_event.clear ()
		self.window.show_all ()

	def generateAccountsFrames(self):
		# Create widgets for each email account and pack them into the table
		accounts = dict ()
		for username in self.config.get_usernames ():
			frame = gtk.Frame (username)
			bbox = gtk.HButtonBox ()
			configure = gtk.Button (stock=gtk.STOCK_PREFERENCES)
			delete = gtk.Button (stock=gtk.STOCK_DELETE)
			accounts.update ( {username:(frame, bbox, configure, delete)}  )

			frame.set_border_width (10)
			frame.add (bbox)
			bbox.set_border_width (5)

			bbox.set_layout (gtk.BUTTONBOX_END)
			bbox.add (configure)
			configure.connect ('clicked', self.configureAccount, username)
			bbox.add (delete)
			delete.connect ('clicked', self.deleteAccount, username)

			frame.show ()
			bbox.show ()
			configure.show ()
			delete.show ()
		return accounts

	def configureAccount(self, widget, username=None):
		with self.gConns_lock:
			if username:
				for gConn in self.gConns.values ():
					if gConn.getUsername () == username:
						gConn.configure (self.config)
			else:
				try:
					gConn = GmailConn (config=self.config)
					self.gConns.update ({gConn.getUsername ():gConn})
					if self.onNewGConn:
						self.onNewGConn (gConn, self.onNewGConnArgs)
				except GmailConn.CancelledError:
					return
		# Update window
		for username, widgets in self.accounts.iteritems ():
			self.window_vbox.remove (widgets[0])
		self.accounts = self.generateAccountsFrames ()
		temp = self.accounts.keys ()
		temp.sort ()
		for username in temp:
			self.window_vbox.pack_start (self.accounts[username][0])


	def deleteAccount(self, widget, username):
		self.config.config.remove_section (username)
		self.config.write ()
		self.config.del_password (username)
		self.window_vbox.remove (self.accounts[username][0])
		with self.gConns_lock:
			gConn = self.gConns.pop (username)
			if self.onDeleteGConn:
				if self.onDeleteGConn (gConn, self.onDeleteGConnArgs) == False:
					pass
				else:
					gConn.stop ()
					del gConn
			else:
				gConn.stop ()
				del gConn


class NotifierConfig:
	"""A configuration object for gmail-notifier. The constructor takes a list of config files."""

	class Error(Exception):
		pass

	class AlreadyRunningError(Error):
		pass

	def __init__(self, files, onNewGConn=None, onNewGConnArgs=None, onDeleteGConn=None, onDeleteGConnArgs=None):
		self.onNewGConn = onNewGConn
		self.onNewGConnArgs = onNewGConnArgs
		self.onDeleteGConn = onDeleteGConn
		self.onDeleteGConnArgs = onDeleteGConnArgs
		self.readConfigFiles (files)

		self.Keyring = keyring.Keyring ('gmail-notifier', 'mail.google.com', 'https')

	def write(self):
		self.config.write (open (os.path.expanduser ('~/.gmail-notifier.conf'), 'w'))

	def readConfigFiles(self, files):
		self.config = ConfigParser.SafeConfigParser ()
		self.config.read (files)

	def showConfigWindow(self, gConns, gConns_lock, onNewGConn=None, onNewGConnArgs=None, onDeleteGConn=None, onDeleteGConnArgs=None):
		gtk.gdk.threads_enter ()
		n = NotifierConfigWindow (
				self,
				gConns,
				gConns_lock,
				(onNewGConn, self.onNewGConn)[onNewGConn == None],
				(onNewGConnArgs, self.onNewGConnArgs)[onNewGConnArgs == None],
				(onDeleteGConn, self.onDeleteGConn)[onDeleteGConn == None],
				(onDeleteGConnArgs, self.onDeleteGConnArgs)[onDeleteGConnArgs == None]
				)
		gtk.gdk.threads_leave ()
		n.close_event.wait ()

	def set_onNewGConn(self, onNewGConn, onNewGConnArgs=None):
		self.onNewGConn = onNewGConn
		self.onNewGConnArgs = onNewGConnArgs

	def set_onDeleteGConn(self, onDeleteGConn, onDeleteGConnArgs=None):
		"""This method is called *AFTER* popping gConn from gConns, but *BEFORE* deleting the removed gConn

		def onDeleteGConn (gConn, onDeleteGConnArgs):
			...
		
		if you return 'False', the gConn object will not be deleted, but it will already be removed from config
		and gConns. Do not add it back to gConns, this is mostly designed for additional cleanup before the
		gConn is destroyed, not to prevent its destruction

		ANY other return value will allow gConn to be deleted
		"""
		self.onDeleteGConn = onDeleteGConn
		self.onDeleteGConnArgs = onDeleteGConnArgs

	def get_usernames(self):
		return self.config.sections ()

	def add_username(self, username, suppress_duplicates=True):
		try:
			self.config.add_section (username)
		except ConfigParser.DuplicateSectionError:
			if not suppress_duplicates:
				raise

	def get_password(self, username):
		return self.Keyring.get_credentials (username)
		#return self.config.get (username, 'password')

	def set_password(self, username, password):
		self.Keyring.set_credentials (username, password)
		#self.config.set (username, 'password', password)

	def del_password(self, username):
		self.Keyring.delete_credentials (username)

	def get_proxy(self, username):
		return self.config.get (username, 'proxy')

	def set_proxy(self, username, proxy):
		self.config.set (username, 'proxy', proxy)

	def get_ac_polling(self, username):
		return self.config.getint (username, 'ac_polling')

	def set_ac_polling(self, username, ac_polling):
		self.config.set (username, 'ac_polling', str (ac_polling))

	def get_battery_polling(self, username, consider_disable=True):
		if consider_disable:
			return (self.config.getint (username, 'battery_polling'),0)[self.config.getboolean (username, 'battery_disable')]
		else:
			return self.config.getint (username, 'battery_polling')

	def set_battery_polling(self, username, battery_polling, battery_disable=False):
		self.config.set (username, 'battery_polling', str (battery_polling))
		self.config.set (username, 'battery_disable', str (battery_disable))

	def get_battery_disable(self, username):
		return self.config.getboolean (username, 'battery_disable')

	def set_battery_disable(self, username, battery_disable):
		self.config.set (username, 'battery_disable', str (battery_disable))
