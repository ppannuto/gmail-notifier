#!/usr/bin/env python

# gmailLib 0.5 by Pat Pannuto <pat.pannuto@gmail.com>
# based loosely on gmailatom 0.0.1 by Juan Grande <juan.grande@gmail.com> from the original gmail-notify

from xml import sax
from xml.sax import saxutils
from xml.sax import make_parser
from xml.sax import ContentHandler
from xml.sax.handler import feature_namespaces
from xml.utils.iso8601 import parse as parse_time

import os
import gtk
import glib
import gobject
import ConfigParser
import urllib2
import threading
import logging
from time import time,asctime,localtime

try:
	import pynotify
except ImportError:
	pass


class GmailConfigWindow():
	"""Show a preferences window to configure a gConn object. Requires a valid ConfigParser object to read/write to"""

	DEFAULT_AC_POLL = 20
	DEFAULT_BATTERY_POLL = 60

	def __init__(self, config, gConn=None, username=None, _=lambda s:s):
		"""Shows a preferences dialog for a gConn object. If a gConn object is supplied, all relevant settings
		will be updated on the object, including a call to resetCredentials (e.g. this is a very appropriate
		response resolving an AuthenticationError raised by a gConn object)
		"""
		self.close_event = threading.Event ()

		# Copy objects
		self.config = config
		self.gConn = gConn

		if not username and gConn:
			username = gConn.getUsername ()

		# Set up the top-level window
		#self.window = gtk.Window ()
		self.window = gtk.Dialog ()
		if username:
			### Configure username -- e.g. Configure notifier@gmail.com
			self.window.set_title (_('Configure %s') % username)
		else:
			self.window.set_title (_('Configure a new account'))
		try:
			self.window.set_icon_from_file ('nomail.png')
		except:
			pass
		self.window.set_position (gtk.WIN_POS_CENTER)
		self.window.set_default_size (400, 100)
		self.window.set_modal (True)

		# Add a vbox to hold the window contents
		#self.window_vbox = gtk.VBox ()
		#self.window.add (self.window_vbox)
		self.window_vbox = self.window.get_content_area ()

		# Add a table to align configuration options nicely
		self.table = gtk.Table (rows=2, columns=2)
		self.window_vbox.pack_start (self.table)
		self.table.show ()

		self.username_label = gtk.Label (_('Username'))
		self.username_entry = gtk.Entry ()
		if (username):
			self.username_entry.set_text (username)
		self.username_entry.connect ('activate', self.onClose)
		self.table.attach (self.username_label, 0, 1, 0, 1)
		self.table.attach (self.username_entry, 1, 2, 0, 1)
		self.username_label.show ()
		self.username_entry.show ()

		self.password_label = gtk.Label (_('Password'))
		self.password_entry = gtk.Entry ()
		self.password_entry.set_visibility (False)
		self.password_entry.connect ('activate', self.onClose)
		self.table.attach (self.password_label, 0, 1, 1, 2)
		self.table.attach (self.password_entry, 1, 2, 1, 2)
		self.password_label.show ()
		self.password_entry.show ()

		### Toggle that controls ******** or password
		self.show_password_checkbutton = gtk.CheckButton (_('Show Password'))
		self.show_password_checkbutton.active = False
		self.show_password_checkbutton.connect ('toggled', self.onShowPasswordToggle)
		self.table.attach (self.show_password_checkbutton, 1, 2, 2, 3)
		self.show_password_checkbutton.show ()

		#Call the rest of the options 'advanced' and put them in an expander
		### Advanced options
		self.expander = gtk.Expander (_('Advanced'))
		self.window_vbox.pack_start (self.expander)
		self.expander.show ()

		self.expander_table = gtk.Table (rows=4, columns=2)
		self.expander.add (self.expander_table)
		self.expander_table.show ()

		self.proxy_label = gtk.Label (_('Proxy'))
		self.proxy_entry = gtk.Entry ()
		self.proxy_entry.connect ('activate', self.onClose)
		try:
			self.proxy_entry.set_text (self.config.get_proxy (username))
		except ConfigParser.Error:
			pass
		self.expander_table.attach (self.proxy_label, 0, 1, 0, 1)
		self.expander_table.attach (self.proxy_entry, 1, 2, 0, 1)
		self.proxy_label.show ()
		self.proxy_entry.show ()

		### How often (in seconds) the notifier polls when on AC power
		self.ac_polling_label = gtk.Label (_('AC Polling Frequency (secs)'))
		self.ac_polling_entry = gtk.SpinButton ()
		self.ac_polling_entry.set_numeric (True)
		self.ac_polling_entry.set_increments (5, 5)
		self.ac_polling_entry.set_range (20, 600)
		try:
			self.ac_polling_entry.set_value (self.config.get_ac_polling (username))
		except ConfigParser.Error:
			self.ac_polling_entry.set_value (self.DEFAULT_AC_POLL)
		self.expander_table.attach (self.ac_polling_label, 0, 1, 1, 2)
		self.expander_table.attach (self.ac_polling_entry, 1, 2, 1, 2)
		self.ac_polling_label.show ()
		self.ac_polling_entry.show ()

		### How often (in seconds) the notifier polls when on battery power
		self.battery_polling_label = gtk.Label (_('Battery Polling Frequency (secs)'))
		self.battery_polling_entry = gtk.SpinButton ()
		self.battery_polling_entry.set_numeric (True)
		self.battery_polling_entry.set_increments (5, 5)
		self.battery_polling_entry.set_range (20, 600)
		try:
			self.battery_polling_entry.set_value (self.config.get_battery_polling (username, consider_disable=False))
		except ConfigParser.Error:
			self.battery_polling_entry.set_value (self.DEFAULT_BATTERY_POLL)
		self.expander_table.attach (self.battery_polling_label, 0, 1, 2, 3)
		self.expander_table.attach (self.battery_polling_entry, 1, 2, 2, 3)
		self.battery_polling_label.show ()
		self.battery_polling_entry.show ()

		### Disable polling when the computer is on battery power
		self.battery_disable_checkbutton = gtk.CheckButton (_('Disable on battery'))
		try:
			self.battery_disable_checkbutton.set_active (self.config.get_battery_disable (username))
		except ConfigParser.Error:
			self.battery_disable_checkbutton.set_active (False)
		self.battery_disable_checkbutton.connect ('toggled', self.onBatteryEnabledToggle)
		self.expander_table.attach (self.battery_disable_checkbutton, 1, 2, 3, 4)
		self.battery_disable_checkbutton.show ()
		
		self.battery_polling_entry.set_sensitive (not self.battery_disable_checkbutton.get_active ())


		# Create an hbox to hold Cancel/Close
		self.hbox = gtk.HBox ()
		self.window_vbox.pack_start (self.hbox)
		self.hbox.show ()

		self.cancel_button = gtk.Button (stock=gtk.STOCK_CANCEL)
		self.cancel_button.connect ('clicked', self.onCancel)
		self.hbox.pack_start (self.cancel_button)
		self.cancel_button.show ()

		self.close_button = gtk.Button (stock=gtk.STOCK_CLOSE)
		self.close_button.connect ('clicked', self.onClose)
		self.hbox.pack_start (self.close_button)
		self.close_button.show ()

		# We're all set up, show and go
		self.window.run ()

	def onShowPasswordToggle(self, widget, user_params=None):
		if widget.get_active ():
			self.password_entry.set_visibility (True)
		else:
			self.password_entry.set_visibility (False)

	def onBatteryEnabledToggle(self, widget, user_params=None):
		if widget.get_active ():
			self.battery_polling_entry.set_sensitive (False)
		else:
			self.battery_polling_entry.set_sensitive (True)

	def onCancel(self, widget, user_params=None):
		self.window.destroy ()
		self.close_event.set ()

	def onClose(self, widget, user_params=None):
		username = self.username_entry.get_text ()
		password = self.password_entry.get_text ()
		proxy = self.proxy_entry.get_text ()
		ac_polling = int (self.ac_polling_entry.get_value ())
		battery_polling = int (self.battery_polling_entry.get_value ())
		battery_disable = self.battery_disable_checkbutton.get_active ()

		if username == '':
			#gtk.gdk.threads_enter ()
			dialog = gtk.MessageDialog (buttons=gtk.BUTTONS_OK, type=gtk.MESSAGE_ERROR)
			dialog.set_position (gtk.WIN_POS_CENTER)
			dialog.set_modal (True)
			dialog.set_markup (_('Error!') + '\n\n' + _('Username is required!'))
			dialog.run ()
			dialog.destroy ()
			#gtk.gdk.threads_leave ()
			return False

		try:
			config_password = self.config.get_password (username)
		except ConfigParser.Error:
			config_password = None

		if password == '' and config_password == None:
			dialog = gtk.MessageDialog (buttons=gtk.BUTTONS_OK, type=gtk.MESSAGE_ERROR)
			dialog.set_position (gtk.WIN_POS_CENTER)
			dialog.set_modal (True)
			dialog.set_markup (_('Error!') + '\n\n' + ('Password is required!'))
			dialog.run ()
			dialog.destroy ()
			return False
		
		if username.find ('@') == -1:
			username += '@gmail.com'
		self.config.add_username (username)
		self.config.set_password (username, (password, config_password)[password == ''])
		self.config.set_proxy (username, proxy)
		self.config.set_ac_polling (username, str (ac_polling))
		self.config.set_battery_polling (username, str (battery_polling))
		self.config.set_battery_disable (username, str (battery_disable))
		self.config.write ()

		if self.gConn:
			self.gConn.set_ac_frequency (ac_polling)
			self.gConn.set_battery_frequency ((battery_polling,0)[battery_disable])
			self.gConn.resetCredentials (username, self.config.get_password (username), self.config.get_proxy (username))

		self.window.destroy ()
		self.close_event.set ()


class Email():
	title = ""
	summary = ""
	link = ""
	id = ""
	modified = 0
	author_name = ""
	author_emailaddr = ""

	def dict(self):
		temp = {}
		temp['title'] = self.title
		temp['summary'] = self.summary
		temp['link'] = self.link
		temp['id'] = self.id
		temp['modified'] = self.modified
		temp['author_name'] = self.author_name
		temp['author_emailaddr'] = self.author_emailaddr
		return temp

class GmailXmlHandler(ContentHandler):
	"""A SAX class to parse gmail atom feeds and strip out each of the messages"""

	# Tags
	TAG_FEED = "feed"
	TAG_TITLE = "title"
	TAG_FULLCOUNT = "fullcount"
	TAG_LINK = "link"
	TAG_MODIFIED = "modified"
	TAG_ID = "id"
	TAG_ENTRY = "entry"
	TAG_SUMMARY = "summary"
	TAG_AUTHOR = "author"
	TAG_NAME = "name"
	TAG_EMAIL = "email"

	# Path the information
	PATH_FULLCOUNT = [ TAG_FEED, TAG_FULLCOUNT ]
	PATH_MODIFIED = [ TAG_FEED, TAG_MODIFIED ]
	
	PATH_EMAIL_TITLE = [ TAG_FEED, TAG_ENTRY, TAG_TITLE ]
	PATH_EMAIL_SUMMARY = [ TAG_FEED, TAG_ENTRY, TAG_SUMMARY ]
	PATH_EMAIL_MODIFIED = [ TAG_FEED, TAG_ENTRY, TAG_MODIFIED ]
	PATH_EMAIL_ID = [ TAG_FEED, TAG_ENTRY, TAG_ID ]
	PATH_EMAIL_AUTHOR_NAME = [ TAG_FEED, TAG_ENTRY, TAG_AUTHOR, TAG_NAME ]
	PATH_EMAIL_AUTHOR_EMAILADDR = [ TAG_FEED, TAG_ENTRY, TAG_AUTHOR, TAG_EMAIL ]

	# local vars
	modified = 0

	# Error logging
	logger = logging.getLogger ('gmailLib')

	def __init__(self):
		self.path = list ()
		self.emails = list ()
		self.email_count = 0
		self.modified = 0

	def startDocument(self):
		self.path = list ()
		self.emails = list ()
		self.email_count = 0
		self.modified = 0

	def endDocument(self):
		pass

	def startElement(self, name, attrs):
		self.path.append (name)
		
		#if this the start of a new email, we're more interested:
		if name == self.TAG_ENTRY:
			self.emails.append (Email ())

		#if this is a link field (in an email, not the feed itself...), grab the link and message_id
		if name == self.TAG_LINK:
			link = attrs.get("href")
			#check if this link is an email or the main RSS feed link
			if link.find("message_id=") != -1:
				self.emails[-1].link = link

	def endElement(self, name):
		last = self.path.pop ()
		if last != name:
			self.logger.debug ("Scoping error? Name: " + name + ", Last: " + last)
			self.logger.debug ("self.emails: " + str (self.emails))
			raise ParseError ("Scoping mismatch in endElement array (BUG)")
	
	def characters(self, content):
		if (self.path == self.PATH_FULLCOUNT):
			self.email_count = int(content)

		if (self.path == self.PATH_MODIFIED):
			#Correct google's bizzare timestamp
			if (content[11:13] == '24'):
				content = content[0:11] + '00' + content[13:]
			self.modified = parse_time(content)

		if (self.path == self.PATH_EMAIL_TITLE):
			self.emails[-1].title += content

		if (self.path == self.PATH_EMAIL_SUMMARY):
			self.emails[-1].summary += content

		if (self.path == self.PATH_EMAIL_MODIFIED):
			#Correct google's bizzare timestamp
			if (content[11:13] == '24'):
				content = content[0:11] + '00' + content[13:]
			self.emails[-1].modified = parse_time(content)

		if (self.path == self.PATH_EMAIL_ID):
			self.emails[-1].id += content

		if (self.path == self.PATH_EMAIL_AUTHOR_NAME):
			self.emails[-1].author_name += content

		if (self.path == self.PATH_EMAIL_AUTHOR_EMAILADDR):
			self.emails[-1].author_emailaddr += content



class GmailConn:
	"""A 'Connection to Gmail' object. This class is the primary (only) interface to this library

USAGE:
	Instantiate a GmailConn object: gConn = GmailConn (username="username@gmail.com", password="password")

	By its nature, a gConn object must access the network with some frequency, as is obviously suceptable to
	all of the quirks of network programming. gConn provides two interfaces, which you are free to mix, that
	will abstract this if you so choose.

	Once initiated, all of the gConn.get* methods are valid. Note that each object takes an optional Update
	parameter with a default value of None. There are 3 valid values for Update, note 'None' may and 'True' will BLOCK:
		None -- (DEFAULT) if self.last_update > self.frequency then query GMail before returning. In an effort
			to simplfy caller's implementation, the cached value will be returned if the update fails,
			to explicitly check if the information is up to date, use Update=True, or gConn.isConnected
		True -- A new scrape of GMail will be forced.  If the update fails, a GmailConn.ConnectionError will
			be raised.
		False - Returns the cached data, ignoring self.last_update time. This call is gaurenteed to be non-blocking


	Alternatively, you may call gConn.start, which will spawn a daemon thread that continuously updates the email
	data every self.frequency seconds.  Whenever gConn determines it has 'new' new mail, it will call self.onNewMail (see
	Gmail.Conn.set_onNewMail for prototype / usage).
	
	Note, some care must be taken after calling start, specifically, you may no longer edit any gConn variables (onNewMail,
	frequency, etc) directly, rather you must use the thread-safe gConn.set_onNewMail() methods instead.


	So long as you only use the exposed methods, a gConn object is fully reentrant.

OPTIONAL ARGUMENTS:
	proxy=None
		If you need to use a proxy for your network, specify it here

	notifications=True
		When a new mail arrives, gConn will use the pynotify module to display a notification to the user of a
		the new mail(s).  It relies on the same internal bookkeeping of 'new' mails as the rest of the module

	start=False
		Identical to calling gConn.start

	onUpdate=None, also GmailConn.set_onUpdate
	onUpdateArgs=None
		Sets the callback function (and args to pass), see GmailConn.set_onUpdate

	onNewMail=None, also GmailConn.set_onNewMail
	onNewMailArgs=None
		Sets the callback function (and args to pass), see GmailConn.set_onNewMail

	onDisconnect=None, also GmailConn.set_onDisconnect
	onDisconnectArgs=None
		Sets the callback function (and args to pass), see GmailConn.set_onDisconnect

	onAuthenticationError=None, also GmailConn.set_onAuthenticationError
	onAuthenticationErrorArgs=None
		Sets the callback function (and args to pass), see GmailConn.set_onAuthenticationError
	
	frequency=TIMEOUT [default: 20], also GmailConn.set_frequency()
		The frequncy at which to poll GMail in seconds.
		NOTE: Values < 20sec are not recommended as GMail may get mad at you...

	disconnect_threshold=THRESHOLD [default: 60], also GmailConn.set_disconnect_threshold()
		The amount of time allowed to pass between successful updates before gConn will consider itself disconnected

	logLevel=logging.WARNING, also GmailConn.set_logLevel()
		The level at which to log, from the standard python logging module
	"""

	realm = "New mail feed"
	host = "https://mail.google.com"
	url = host + "/mail/feed/atom"

	TIMEOUT = 20		# Number of seconds until data is considered 'stale'
	THRESHOLD = 60		# Number of seconds allowed between successful updates until gConn is considered disconnected
	last_update = 0		# The time (time.time()) of the last _successful_ update

	class Error(Exception):
		"""Base class for exceptions in this module"""
		pass

	class UnrecoverableError(Error):
		"""This error is never directly raised, rather, it is subclassed for various unrecoverable conditions"""
		pass

	class CancelledError(Error):
		"""The user cancelled the input box when instantiating a gConn with config != None"""
		pass

	class AuthenticationError(Error):
		"""This error is raised if we receive a 401 Unauthorized. It means the username/password is incorrect"""
		pass

	class ParseError(Error):
		"""The library had some type of trouble parsing the xml feed.  This is likely a transient error, however
		if it persists, it may indicate that google changed the structure of their feed, and the code needs to be updated

		Callers may safely ignore this error, but they should be aware of it.
		"""
		pass

	class UninitializedError(Error):
		"""An attempt to call one of gConn's functions was made prior to calling 'start'"""
		pass

	class AlreadyInitalizedError(Error):
		"""A call was made to 'start' after the object was already running"""
		pass

	class ConnectionError(Error):
		"""Raised when using a GmailConn.get* method with Update=True and a connection to GMail could not be esatblished.

		NOTE: These types of errors are usually transient, (e.g. lost connection)
		"""

	def __init__(
			self,
			username=None,
			notifications=True,
			start=False,
			disconnect_threshold=THRESHOLD,
			config=None,
			logLevel=logging.WARNING
			):
		
		self.logLevel = logLevel
		logging.basicConfig (level=self.logLevel, format="%(asctime)s [%(levelname)s]\t{%(thread)s} %(name)s:%(lineno)d %(message)s")
		self.logger = logging.getLogger ('gmailLib')
		
		# Since we provide a relatively flexible init, we have to do a little sanity checking on arguments
		if username == None and config == None:
			raise TypeError ('One of username or config must be defined!')
		if username != None and config == None and start == True:
			raise TypeError ('Cannot start with just a username (and no config)')
		
		# Copy in relevant initialization variables
		self.username = username
		self.notifications = notifications
		if (notifications):
			import pynotify
			if not pynotify.init ('Gmail Notifier'):
				self.logger.critical ('Error loading %s' % 'pynotify')
				raise ImportError
		self.disconnect_threshold = disconnect_threshold
		
		# Set up threading
		self.lock = threading.RLock ()
		self.network_lock = threading.Lock ()

		# Load images as into pixbufs
		try:
			self.ICON_NOCONN = gtk.gdk.pixbuf_new_from_file ('noconnection.png')
		except glib.GError:
			self.ICON_NOCONN = None
		try:
			self.ICON_AUTHERR = gtk.gdk.pixbuf_new_from_file ('autherr.png')
		except glib.GError:
			self.ICON_AUTHERR = None
		try:
			self.ICON_NOMAIL = gtk.gdk.pixbuf_new_from_file ('nomail.png')
		except glib.GError:
			self.ICON_NOMAIL = None
		try:
			self.ICON_NEWMAIL = gtk.gdk.pixbuf_new_from_file ('newmail.png')
		except glib.GError:
			self.ICON_NEWMAIL = None
		
		# Initialize state
		self.started = False
		self.events = list ()
		self.shown = list ()
		self.auth_error = False
		self.auth_error_running = False
		self.last_modified = 0
		self.disconnected = True
		self.onNewMail = None
		self.onUpdate = None
		self.onAuthenticationError = None
		self.onDisconnect = None
		
		# Set up the XML parser
		self.xml_parser = GmailXmlHandler()
		
		# Read in configuration if provided
		if config:
			if self.username:
				# We want data on the username from the provided config file
				self.resetCredentials (self.username, config.get_password (self.username), config.get_proxy (self.username))
				self.ac_frequency = config.get_ac_polling (self.username)
				self.battery_frequency = config.get_battery_polling (self.username)
				self.frequency = self.ac_frequency
			else:
				# We are creating a new gConn here w/ a new entry
				self.logger.debug ('Creating a new gConn with configure')
				self.configure (config)
				try:
					self.ac_frequency = config.get_ac_polling (self.username)
					self.battery_frequency = config.get_battery_polling (self.username)
					self.frequency = self.ac_frequency
				except (AttributeError, ConfigParser.Error):
					raise self.CancelledError
		
		# Start the gConn object if requested (not default)
		if (start):
			self.start ()

		self.logger.debug ("GmailConn.__init__ completed successfully")

	def configure(self, config):
		"""Spawns a configuration window for this gConn object, which will be updated. (You can use gConn.getUsername
		to retrieve the username after this call if you so require)"""
		locals = threading.local ()
		self.logger.debug ('GMailConn configure called')
		locals.w = GmailConfigWindow (config, gConn=self)
		self.logger.debug ('GMailConn configure completed')


	def start(self):
		"""(nonblocking) Spawns an updater thread that will poll GMail. You may poll the gConn object for updates,
		or register a callback as gConn.onNewMail (NOTE: Once a gConn object is start'ed, use gConn.set_onNewMail to
		change this in a thread-safe manner)"""
		with self.lock:
			if self.started:
				raise self.AlreadyInitalizedError

			self.thread = threading.Thread (group=None, target=self.updater)
			self.thread.daemon = True
			self.thread.name = 'GmailLib: gConn::updater - ' + self.username
			self.thread.start ()
			self.started = True

	def restart(self, frequency):
		"""(nonblocking) Call this after a call to stop to continue the updater thread again"""
		with self.lock:
			self.frequency = frequency
			for event in self.events ():
				event.set ()

	def stop(self):
		"""(nonblocking) Stops the updater thread, returns the currently set frequency, which can be passed to continue later"""
		with self.lock:
			freq = self.frequency
			self.frequency = 0
			return freq

	def set_onUpdate(self, onUpdate, onUpdateArgs=None):
		"""Sets the onUpdate callback.  This function is called whenever the GMail atom feed it updated.  This is
		at the discretion of _Google_.  The feed contains a 'modified' field, and this function is called any time
		that this field is changed.
		def onUpdate(gConn, onUpdateArgs)
			gConn		-- A refrence to the calling object. Note: It is _recommended_, but not required that
					   any calls to this object's get* methods use Update=False, otherwise, you may end
					   up triggering an update, which will call this method again...
			onUpdateArgs	-- Arguments supplied here will be passed to the callback
		
		*** This callback is called _whenever_ gConn determines there are 'new' unread emails.  It may be called from
		the updater thread OR from a call to gConn.get* with Update=None or Update=True ***
		"""
		with self.lock:
			self.onUpdate = onUpdate
			self.onUpdateArgs = onUpdateArgs

	def set_onNewMail(self, onNewMail, onNewMailArgs=None):
		"""Sets the onNewMail callback.  This function is called whenever a 'new' unread email is recieved.
		def onNewMail(gConn, newEmails, onNewMailArgs)
			gConn		-- A refrence to the calling object. See the warning in set_onUpdate
			newEmails	-- A list of emails that have not been _shown_ to the caller before. This means if there are
					   3 unread emails, and a 4th arrives, you will only get ONE email (the newest) in this argument
			onNewMailArgs	-- Arguments supplied here will be passed to the callback

		*** This callback is called _whenever_ gConn determines there are 'new' unread emails.  It may be called from
		the updater thread OR from a call to gConn.get* with Update=None or Update=True ***
		"""
		with self.lock:
			self.onNewMail = onNewMail
			self.onNewMailArgs = onNewMailArgs

	def set_onDisconnect(self, onDisconnect, onDisconnectArgs=None):
		"""Sets the onDisconnect callback.  Called whenever time.time() - gConn.last_update > gConn.disconnect_threshold.
		def onDisconnect(onDisconnectArgs, [gConn])
			gConn			-- A reference to the calling object. See the warning in set_onUpdate
			onDisconnectArgs	-- Arguments supplied here will be passed to the callback

		*** This callback is called _whenever_ gConn determines it is disconnected.  It may be called from
		the updater thread OR from a call to gConn.get* with Update=None or Update=True ***
		"""
		with self.lock:
			self.onDisconnect = onDisconnect
			self.onDisconnectArgs = onDisconnectArgs

	def set_onAuthenticationError(self, onAuthenticationError, onAuthenticationErrorArgs=None):
		"""Sets the onAuthenticationError callback.  In the event of an authentication error (incorrect username/password),
		a gConn object will first attempt to call this function. If it is not defined, an AuthenticationError will be raised

		def onAuthenticationError(onAuthenticationError, [gConn])
			gConn			-- A reference to the calling object. See the warning in set_onUpdate
			onAuthenticationErrorArgs	-- Arguments supplied here will be passed to the callback

		Note: If you application daemonizes gConn (that is, calls start), you _must_ implement this method, otherwise
		the uncaught AuthenticationError will simply kill off the 'updater' thread

		Note: An authentication error will suspend the updater thread until a call to resetCredentials is made
		"""
		with self.lock:
			self.onAuthenticationError = onAuthenticationError
			self.onAuthenticationErrorArgs = onAuthenticationErrorArgs

	def set_power(self, ac):
		with self.lock:
			if ac:
				for event in self.events:
					event.set ()
				self.set_frequency (self.ac_frequency)
			else:
				self.set_frequency (self.battery_frequency)

	def set_frequency(self, frequency=TIMEOUT):
		"""Sets frequency (in secs), if unspecified, reset to default (20). Note, it may take up to
		frequency (previous value) seconds for this update to take effect.  If your goal is to suspend
		the notifier, a better choice would likely be to stop() and then start again later
		"""
		with self.lock:
			self.frequency = frequency
		self.logger.debug ('Frequency set to ' + str (frequency))

	def set_ac_frequency(self, frequency=TIMEOUT):
		with self.lock:
			self.ac_frequency = frequency

	def set_battery_frequency(self, frequency=TIMEOUT):
		with self.lock:
			self.battery_frequency = frequency

	def set_logLevel(self, logLevel):
		"""Sets the log level for gmailLib. Expects a log level from the standard python logging module (e.g. logging.DEBUG)"""
		with self.lock:
			self.logger.setLevel (logLevel)

	def set_showNotifications(self, notifications=True):
		"""Should this object display a notifications automatically on new mail?"""
		with self.lock:
			self.notifications = notifications

	def update(self, async=False, force_callbacks=False):
		"""Force an update. If the async parameter is True, a one-off thread will be spawned to try to update. Otherwise,
		this function will block until the update is complete.

		The force_callbacks parameter will cause onUpdate or onDisconnect (whichever is appropriate) during this update,
		regardless of whether it would have otherwise been called.
		
		Note: If an async update fails for any reason, you will not recieve any indication (except perhaps
		onAuthenticationError), but any other transient error will be lost.
		"""
		if async:
			t = threading.Thread (target=self.refreshInfo, name='GmailLib: gConn::async_update', args=(force_callbacks,))
			t.daemon = True
			t.start ()
		else:
			return self.refreshInfo (force_callbacks)

	def updater(self):
		"""Internal -- There is no reason to call this directly"""
		locals = threading.local ()
		locals.event = threading.Event ()
		self.lock.acquire ()
		self.events.append (locals.event)
		self.lock.release ()
		while True:
			self.lock.acquire ()
			locals.auth_error = self.auth_error
			locals.frequency = self.frequency
			self.lock.release ()
			if not locals.auth_error and (locals.frequency not in (0,-1)):
				try:
					self.refreshInfo ()
				except self.ParseError as e:
					self.logger.warning (str(e))
			if locals.frequency == 0 or locals.frequency == -1:
				locals.event.wait ()
			elif locals.frequency < 20:
				logger.warning (self.getUsername () + ': Bad polling frequency (' + str (locals.frequency) + ') defaulting to ' + str (self.TIMEOUT))
				locals.event.wait (timeout=self.TIMEOUT)
			else:
				locals.event.wait (timeout=locals.frequency)
			locals.event.clear ()

	def notify(self, emails=None, check_connected=True, status_icon=None, _=lambda s:s):
		"""Show the newest email. You may provide a list of email dicts (as returned from getAllEmails) in emails to leverage
		the notification engine to show an update for a subset of emails. Otherwise the cached email list will be used. The
		emails argument is assumed to be sorted such that the newest email is emails[0].

		If check_connectd=True, the notification engine will prepend a warning to the notification if isConnected returns False
		
		Note: This function will not automatically update the internal email list
		
		Note: This function will attempt to use pynotify. The caller is responsible for catching the NameError if it occurs.
		"""
		title = ''
		text = ''
		icon = self.ICON_NOCONN
		
		self.lock.acquire ()
		connected = self.isConnected (update=False)
		
		title += self.username + ': '
		
		if emails:
			show = emails
		else:
			show = list ()
			for email in self.xml_parser.emails:
				show.append (email.dict ())
		
		if self.auth_error:
			title += _('Authentication Error')
			text += _('Bad username or password')
			icon = self.ICON_AUTHERR
		elif check_connected and not connected:
			title += _('Could not connect to GMail')
			if self.last_update:
				### %s is string timestamp returned from asctime(localtime())
				text += _('Last updated %s') % asctime (localtime (self.last_update))
				text += '\n\n'
				if self.xml_parser.email_count == 1:
					### Singular 'message'
					text += _('You had %d unread message at the last update') % self.xml_parser.email_count
				else:
					### Plural 'messages'
					text += _('You had %d unread messages at the last update') % self.xml_parser.email_count
			else:
				text += _('You have not successfully connected to GMail during this session')
		else:
			if len (show) == 0:
				title += _('You have no unread messages')
				text += _('Last updated %s') % asctime (localtime (self.last_update))
				icon = self.ICON_NOMAIL
			elif len (show) == 1:
				title += show[0]['title']
				text += show[0]['summary']
				icon = self.ICON_NEWMAIL
			else:
				### %d always > 1 ('messages' always plural')
				title += _('You have %d unread messages') % self.xml_parser.email_count
				text += _('(newest): ') + show[0]['title'] + '\n\n' + show[0]['summary']
				icon = self.ICON_NEWMAIL
		
		try:
			n = pynotify.Notification (title, text)
			n.set_urgency (pynotify.URGENCY_LOW)
			if status_icon:
				n.attach_to_status_icon (status_icon)
			if icon:
				n.set_icon_from_pixbuf (icon)
			n.show ()
		except gobject.GError as e: #GError: Message did not receive a reply (timeout by message bus)
			# This is likely transient? We'll give it one more shot, then ignore. XXX How does this happen? Should we silently ignore?
			self.logger.warning ('Notifier error: ' + str (e))
			try:
				pynotify.init ('Gmail Notifier')
				n = pynotify.Notification (title, text)
				n.set_urgency (pynotify.URGENCY_LOW)
				if status_icon:
					n.attach_to_status_icon (status_icon)
				if icon:
					try:
						n.set_icon_from_pixbuf (icon)
					except glib.GError as e:
						self.logger.warning ('Issue with notification pixbuf (BUG): ' + str(e))
				n.show ()
			except gobject.GError as e:
				self.logger.error ('Notifier error: ' + str(e))
				self.logger.error ('Giving up -- Notification will not be shown')
		except glib.GError as e:
			self.logger.warning ('Issue with notification pixbuf (BUG): ' + str(e))

		
		self.lock.release ()

	def resetCredentials(self, username, password, proxy=None):
		self.logger.debug ('resetCredentials called for ' + username)
		self.lock.acquire ()
		reload (urllib2)
		
		if (username.rfind("@")) == -1:
			raise ParseError ('Bad username, @ is required', username)

		self.username = username
		
		# initialize authorization handler
		auth_handler = urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password( self.realm, self.host, username, password)
		
		# manage proxy
		if proxy:
			proxy_handler = urllib2.ProxyHandler({'http': proxy})
			self.opener = urllib2.build_opener(proxy_handler, auth_handler)
		else:
			self.opener = urllib2.build_opener(auth_handler)
		
		if self.started:
			self.events[0].set ()
		
		self.auth_error = False
		self.lock.release ()

	def sendRequest(self):
		"""Internal -- There is no reason to call this directly"""
		return self.opener.open(self.url, timeout=10)
#		return open('feed.xml', 'r')

	def refreshInfo(self, force_callbacks=False):
		self.logger.debug ('refreshInfo -- starting...')
		"""Internal -- There is no reason to call this directly"""
		# get the page and parse it
		self.network_lock.acquire ()
		try:
			locals = threading.local ()
			locals.raw_xml = self.sendRequest ().read ()
			self.network_lock.release ()
			self.lock.acquire ()
			raw_xml = sax.parseString (locals.raw_xml, self.xml_parser)
			self.last_update = time ()
			self.auth_error = False
			self.logger.info ("refreshInfo completed successfully at " + asctime (localtime (self.last_update)))
			
			show = list()
			for email in self.xml_parser.emails:
				if email.id not in self.shown:
					self.shown.append (email.id)
					show.append (email.dict ())

			if len (show):
				if not self.getUnreadMessageCount (False):
					raise self.ParseError ('len (show): %d does not match getUnreadMessageCount: %d' % (len (show), self.getUnreadMessageCount (False)))
			
			if len (show) and self.notifications:
				self.notify (show)

			if len (show) and self.onNewMail:
				copy = threading.local ()
				copy.show = show
				copy.onNewMail = self.onNewMail
				copy.onNewMailArgs = self.onNewMailArgs
				copy.onNewMail (self, copy.show, copy.onNewMailArgs)
			
			if self.last_modified != self.xml_parser.modified or self.disconnected or force_callbacks:
				self.last_modified = self.xml_parser.modified
				self.disconnected = False
				if self.onUpdate:
					copy = threading.local ()
					copy.onUpdate = self.onUpdate
					copy.onUpdateArgs = self.onUpdateArgs
					copy.onUpdate (self, copy.onUpdateArgs)
			
			self.lock.release ()
			return True
		
		except urllib2.URLError as inst:
			self.network_lock.release ()
			self.lock.acquire ()
			try:
				# urllib2 only has one error class URLError, so if it's not an HTTP error,
				# this won't be defined, ugh...
				error = inst.getcode ()
			except AttributeError:
				error = 0
			if error == 401:
				# HTTP 401 -- Unauthorized
				if self.onAuthenticationError:
					self.auth_error = True
					if self.auth_error_running:
						# Another thread is currently calling the onAuthenticationError callback
						self.lock.release ()
						self.logger.debug ('Found auth_error_running == True, suppressing this one')
						return False
					self.logger.debug ('Authentication error -- invoking callback')
					self.auth_error_running = True
					copy = threading.local()
					copy.onAuthenticationError = self.onAuthenticationError
					copy.onAuthenticationErrorArgs = self.onAuthenticationErrorArgs
					copy.onAuthenticationError (self, copy.onAuthenticationErrorArgs)
					self.auth_error_running = False
					self.lock.release ()
				else:
					self.logger.debug ('Authentication error -- No callback defined, raising error')
					self.lock.release ()
					raise self.AuthenticationError
				return False
			# This is almost certainly a transient error, likely due to a lost connection, we don't really care
			# we'll just try to update again in a minute and keep polling until we can actually connect again.
			self.logger.info ("urllib Error: " + str(inst) + " (ignored)")
			if (time() - self.last_update) > self.disconnect_threshold or force_callbacks:
				self.logger.info ('Disconnected! (last_update: ' + asctime (localtime (self.last_update)) + ')')
				self.disconnected = True
				copy = threading.local ()
				copy.onDisconnect = self.onDisconnect
				copy.onDisconnectArgs = self.onDisconnectArgs
				copy.onDisconnect (self, copy.onDisconnectArgs)
			
			self.lock.release ()
			return False

	def u(self, update, use_disconnect_threshold=False):
		if update == True:
			if self.refreshInfo () == False:
				raise self.ConnectionError
			return True
		
		self.lock.acquire ()
		compare = (self.frequency, self.disconnect_threshold)[use_disconnect_threshold]
		if (time () - self.last_update) > compare:
			self.lock.release ()
			if update == False:
				return False
			return self.refreshInfo ()
		else:
			self.lock.release ()
			return True

	def isConnected(self, update=None):
		"""Call this method to establish if the gConn object believes itself to be connected. This is currently
		defined by having valid data within the last disconnect_threshold seconds. Alternatively, set update=True to force an
		immediate connection validation, even if it has previously connected once in the last disconnect_threshold seconds
		
		Note, calling this with update=True will raise a GmailConn.ConnectionError if the connection fails
		
		Note, calling this with update=True will or update=None may block"""
		return self.u (update, use_disconnect_threshold=True)

	def isAuthenticationError(self):
		"""Returns authentication status in a thread-safe manner"""
		with self.lock:
			return self.auth_error

	def getUsername(self, update=None):
		"""Returns the GMail username associated with this gConn object"""
		locals = threading.local ()
		self.lock.acquire ()
		try:
			locals.username = self.username
		except AttributeError:
			locals.username = None
		self.lock.release ()
		return locals.username

	def getModificationTime(self, update=None):
		"""Returns the timestamp ( as a float analogous to time.time() ) from the RSS feed when the feed was last updated.
		This is an appropriate (best) way to poll if there are any new messages"""
		locals = threading.local ()
		self.u (update)
		self.lock.acquire ()
		locals.ret = self.xml_parser.modified
		self.lock.release ()
		return locals.ret

	def getUnreadMessageCount(self, update=None):
		"""Returns the number of unread messages in the gmail inbox"""
		locals = threading.local ()
		self.u (update)
		with self.lock:
			return self.xml_parser.email_count

	def getNewestEmail(self, update=None):
		"""Returns the newest available email"""
		locals = threading.local ()
		self.u (update)
		self.lock.acquire ()
		if self.xml_parser.email_count == 0:
			self.lock.release ()
			return None
		else:
			locals.ret = self.xml_parser.emails[-1].dict()
			self.lock.release ()
			return locals.ret

	def getAllEmails(self, update=None, limit=10):
		"""Returns all unread messages, note the 'limit' parameter, which may be disabled by setting it < 0"""
		locals = threading.local ()
		self.u (update)
		self.lock.acquire ()
		locals.ret = list()
		locals.cnt = 0
		for email in self.xml_parser.emails:
			if (locals.cnt >= limit) and (limit > 0):
				break
			locals.ret.append(email.dict())
			locals.cnt += 1
		self.lock.release ()
		return locals.ret
