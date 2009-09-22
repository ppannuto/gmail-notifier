import os
import gtk
import logging
import threading
import ConfigParser
from gmailLib import GmailConn

class NotifierConfigWindow:

	def __init__(self, config, gConns):
		self.close_event = threading.Event ()
		self.buildWindow (config, gConns)
		gtk.main ()

	def buildWindow(self, config, gConns):
		# Set up the top-level window
		self.window = gtk.Window ()
		self.window.set_title ('GMail Notifier Preferences')
		self.window.set_position (gtk.WIN_POS_CENTER)

		# Add a vbox to hold the window contents
		self.window_vbox = gtk.VBox ()
		self.window.add (self.window_vbox)

		# Add instructions (Label) at the top of the window
		self.top_label = gtk.Label ('Add, remove, and configure GMail accounts')
		self.window_vbox.pack_start (self.top_label)

		# Add a table to hold all of the account buttons
		self.accounts_table = gtk.Table (rows=1, columns=3)
		self.window_vbox.pack_start (self.accounts_table)

		# Create widgets for each email account and pack them into the table
		self.accounts = list()
		rows = 0
		for username in config.sections ():
			rows += 1
			self.accounts_table.resize (rows=rows, columns=3)
			self.accounts.append (  (gtk.Label (), gtk.Button (stock=gtk.STOCK_PREFERENCES), gtk.Button (stock=gtk.STOCK_DELETE))  )
			# Label
			self.accounts[-1][0].set_text (username)
			alignment = gtk.Alignment (xalign=0)
			alignment.add (self.accounts[-1][0])
			self.accounts_table.attach (alignment, 0, 1, rows-1, rows)
			# Configure Button
			self.accounts[-1][1].set_label ('Configure')
			self.accounts[-1][1].connect ('clicked', self.configureAccount, config, gConns, username)
			alignment = gtk.Alignment (xalign=1)
			alignment.add (self.accounts[-1][1])
			self.accounts_table.attach (alignment, 1, 2, rows-1, rows)
			# Delete Button
			self.accounts[-1][2].connect ('clicked', self.deleteAccount, config, gConns, username)
			alignment = gtk.Alignment (xalign=1)
			alignment.add (self.accounts[-1][2])
			self.accounts_table.attach (alignment, 2, 3, rows-1, rows)

		# 'Add new account' button
		self.new_account_button = gtk.Button (stock=gtk.STOCK_ADD, label="_Add a new account...")
		self.new_account_button.set_label ('_Add a new account...')
		self.new_account_button.connect ('clicked', self.configureAccount, config, gConns)
		alignment = gtk.Alignment (xalign=1.0)
		alignment.add (self.new_account_button)
		self.window_vbox.pack_start (alignment)

		# Close window button
		self.close_button = gtk.Button (stock=gtk.STOCK_CLOSE)
		self.close_button.connect ('clicked', self.onDelete, config, gConns)
		self.window_vbox.pack_start (self.close_button)

		self.close_event.clear ()
		self.window.show_all ()

	def configureAccount(self, widget, config, gConns, username=None):
		if username:
			print ('configureAccount with username ' + username + ' called')
			for gConn in gConns:
				if gConn.getUsername () == username:
					gConn.configure (config)
		else:
			print ('configureAccount with username=None called')
			try:
				gConns.append (GmailConn (config=config))
			except GmailConn.CancelledError:
				print ('configureAccount new account creation cancelled')
		self.buildWindow (config, gConns)
		print ('configureAccount complete')


	def deleteAccount(self, widget, config, gConns, username):
		config.remove_section (username)

	def onDelete(self, widget, config, gConns):
		# XXX
		config.write (open (os.path.expanduser ('~/.gmail-notifier.conf'), 'w'))
		self.window.destroy ()
		self.close_event.set ()


class NotifierConfig:
	"""A configuration object for gmail-notifier. The constructor takes a list of config files.  This object is
	reentrant, and as a consequence may block.  If you need non-blocking access, wrap your any access to the
	config object with try_lock/release_lock (but only if try_lock returned True!)
	"""

	class Error(Exception):
		pass

	class AlreadyRunningError(Error):
		pass

	def __init__(self, files):
		self.lock = threading.RLock ()
		self.readConfigFiles (files)

	def try_lock(self, blocking=0):
		return self.lock.acquire (blocking)

	def release_lock(self):
		self.lock.release ()

	def readConfigFiles(self, files):
		with self.lock:
			self.config = ConfigParser.SafeConfigParser ()
			self.config.read (files)

	def showConfigWindow(self, gConns, gConns_lock):
		print 'a'
		with self.lock:
			print 'b'
			with gConns_lock:
				print 'c'
				gtk.gdk.threads_enter ()
				print 'd'
				n = NotifierConfigWindow (self.config, gConns)
				print 'e'
				gtk.gdk.threads_leave ()
				print 'f'
				n.close_event.wait ()

	def get_usernames(self):
		with self.lock:
			return self.config.sections ()

	def get_password(self, username):
		with self.lock:
			return self.config.get (username, 'password')

	def get_ac_polling(self, username):
		with self.lock:
			return self.config.getint (username, 'ac_polling')

	def get_battery_polling(self, username):
		with self.lock:
			return self.config.getint (username, 'battery_polling')
