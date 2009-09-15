#!/usr/bin/env python

# gmailLib 0.1 by Pat Pannuto <pat.pannuto@gmail.com>
# based loosely on gmailatom 0.0.1 by Juan Grande <juan.grande@gmail.com>

from xml import sax
from xml.sax import saxutils
from xml.sax import make_parser
from xml.sax import ContentHandler
from xml.sax.handler import feature_namespaces
from xml.utils.iso8601 import parse as parse_time

import urllib2
import threading
import logging
from time import time,sleep,asctime,localtime

try:
	import pynotify
except ImportError:
	pass

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
		pass

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
			raise ParseError ("Scoping mismatch in endElement array")
	
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
		None -- (DEFAULT) if self.last_update > self.timeout then query GMail before returning. In an effort
			to simplfy caller's implementation, the cached value will be returned if the update fails,
			to explicitly check if the information is up to date, use Update=True, or gConn.isConnected
		True -- A new scrape of GMail will be forced.  If the update fails, a GmailConn.ConnectionError will
			be raised.
		False - Returns the cached data, ignoring self.last_update time. This call is gaurenteed to be non-blocking


	Alternatively, you may call gConn.start(), which will spawn a worker thread that continuously updates the email
	data every self.timeout seconds.  Whenever gConn determines it has 'new' new mail, it will call self.onNewMail (see
	Gmail.Conn.set_onNewMail for prototype / usage).
	
	Note, some care must be taken after calling start(), specifically, you may no longer edit any gConn variables (onNewMail,
	timeout, etc) directly, rather you must use the thread-safe gConn.set_onNewMail() methods instead.

OPTIONAL ARGUMENTS:
	proxy=None
		If you need to use a proxy for your network, specify it here

	notifications=True
		When a new mail arrives, gConn will use the pynotify module to display a notification to the user of a
		the new mail(s).  It relies on the same internal bookkeeping of 'new' mails as the rest of the module

	start=False
		Identical to calling gConn.start()

	onNewMail=None, also GmailConn.set_onNewMail()
		Sets the callback function, see GmailConn.set_onNewMail()
	
	timeout=TIMEOUT [default: 20], also GmailConn.set_timeout()
		The frequncy at which to poll GMail in seconds.
		_NOTE_: Values < 20sec are not recommended as GMail may get mad at you...

	logLevel=logging.WARNING, also GmailConn.set_logLevel()
		The level at which to log, from the standard python logging module
	"""

	realm = "New mail feed"
	host = "https://mail.google.com"
	url = host + "/mail/feed/atom"

	TIMEOUT = 20	# Number of seconds until data is considered 'stale'
	last_update = 0

	class Error(Exception):
		"""Base class for exceptions in this module"""
		pass

	class UnrecoverableError(Error):
		"""This error is currently unused, but is a placeholder for an unrecoverable error in the library
		
		It exists because every other error in this class can be handled in some manner that would allow the continuation
		of normal function, but if there is any need for a fatal error in the future, it is desireable that a mechanism
		exists to handle that case"""
		pass

	class ParseError(Error):
		"""The library had some type of trouble parsing the xml feed.  This is likely a transient error, however
		if it persists, it may indicate that google changed the structure of their feed, and the code needs to be updated

		Callers may safely ignore this error, but they should be aware of it.
		"""
		pass

	class UninitializedError(Error):
		"""An attempt to call one of gConn's functions was made prior to calling 'start()'"""
		pass

	class AlreadyInitalizedError(Error):
		"""A call was made to 'start()' after the object was already running"""
		pass

	class ConnectionError(Error):
		"""Raised when using a GmailConn.get* method with Update=True and a connection to GMail could not be esatblished.

		NOTE: These types of errors are usually transient, (e.g. lost connection)
		"""

	def __init__(self, username, password, proxy=None, onNewMail=None, onNewMailArgs=None, notifications=True, start=False, timeout=TIMEOUT, logLevel=logging.WARNING):
		# Copy in relevant initialization variables
		self.onNewMail = onNewMail
		self.onNewMailArgs = onNewMailArgs

		self.logLevel = logLevel
		logging.basicConfig (level=self.logLevel, format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s")
		self.logger = logging.getLogger ('gmailLib')

		self.notifications = notifications
		if (notifications):
			import pynotify
			if not pynotify.init ('Gmail Notifier 2'):
				self.logger.critical ("Error loading / initializing pynotify module")
				raise ImportError

		self.timeout = timeout

		# Set up threading
		self.lock = threading.Lock()

		# Initialize locals
		self.shown = list()
		self.last_modified = 0

		# Add @gmail.com if the caller didn't
		if (username.rfind("@gmail.com")) == -1:
			username += "@gmail.com"
			self.logger.info ("Did not get FQ email address, using" + username)
		
		self.xml_parser = GmailXmlHandler()
		
		# initialize authorization handler
		auth_handler = urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password( self.realm, self.host, username, password)
		
		# manage proxy
		if proxy:
			proxy_handler = urllib2.ProxyHandler({'http': proxy})
			opener = urllib2.build_opener(proxy_handler, auth_handler)
		else:
			opener = urllib2.build_opener(auth_handler)
		
		urllib2.install_opener(opener)
		
		# Start the gConn object if requested (not default)
		self.started = False
		if (start):
			self.start()

		self.logger.debug ("GmailConn.__init__ completed successfully")

	def start(self):
		"""(nonblocking) Spawns an updater thread that will poll GMail. You may poll the gConn object for updates,
		or register a callback as gConn.onNewMail (NOTE: Once a gConn object is start()ed, use gConn.set_onNewMail to
		change this in a thread-safe manner)"""
		self.lock.acquire()
		if self.started:
			self.lock.release()
			raise self.AlreadyInitalizedError

		self.thread = threading.Thread (group=None, target=self.updater)
		self.thread.daemon = True
		self.thread.start()
		self.started = True
		self.lock.release()
		self.logger.debug ('updater thread spawned successfully')

	def set_onNewMail(self, onNewMail, onNewMailArgs=None):
		"""Sets the onNewMail callback.  This function is called whenever a 'new' unread email is recieved. The function
		is passed two arguments - onNewMailArgs and newEmails, which is an list of all _newly recieved_ emails (as dicts),
		note this will NOT always be every email in the inbox that GMail considers 'unread', rather, it will be an array
		of all the emails that have not yet been 'shown' to the object owner.

		To get all of the unread emails, or any other information, use the gConn.get* methods with Update=False

		e.g.
			def onNewMail(onNewMailArgs, newEmails)

		*** This callback is called _whenever_ gConn determines there are 'new' unread emails.  It may be called from
		the updater thread OR from a call to gConn.get* with Update=None or Update=True ***
		"""
		self.lock.acquire ()
		self.onNewMail = onNewMail
		self.onNewMailArgs = onNewMailArgs
		self.lock.release ()

	def set_timeout(self, timeout=TIMEOUT):
		"""Sets timeout frequncy to timeout (in secs), if unspecified, reset to default (20). Note, it may take up to
		timeout (previous value) seconds for this update to take effect.  If your goal is to suspend the notifier, a
		better choice would likely be to stop() and then start() again later
		"""
		self.lock.acquire ()
		self.timeout = timeout
		self.lock.release ()

	def set_logLevel(self, logLevel):
		"""Sets the log level for gmailLib. Expects a log level from the standard python logging module (e.g. logging.DEBUG)"""
		self.lock.acquire ()
		self.logger.setLevel (logLevel)
		self.lock.release ()

	def updater(self):
		"""Internal -- There is no reason to call this directly"""
		local = threading.local ()
		while True:
			self.refreshInfo ()
			self.lock.acquire ()
			local.timeout = self.timeout
			self.lock.release ()
			sleep (local.timeout)

	def sendRequest(self):
		"""Internal -- There is no reason to call this directly"""
		return urllib2.urlopen(self.url, timeout=10)
#		return open('feed.xml', 'r')

	def refreshInfo(self):
		"""Internal -- There is no reason to call this directly"""
		# get the page and parse it
		self.lock.acquire ()
		try:
			raw_xml = sax.parseString (self.sendRequest().read(), self.xml_parser)
			self.last_update = time ()
			self.logger.info ("refreshInfo completed successfully at " + asctime (localtime (self.last_update)))
			
			show = list()
			for email in self.xml_parser.emails:
				if email.id not in self.shown:
					self.shown.append (email.id)
					show.append (email.dict())
			
			if len (show):
				if self.notifications:
					import pynotify
					if len (show) == 1:
						n = pynotify.Notification (show[0]['title'], show[0]['summary'])
						n.show()
					else:
						n = pynotify.Notification ('You have ' + str (self.xml_parser.email_count) + ' unread messages',
								'(newest): ' + show[0]['title'] + '\n\n' + show[0]['summary'])
						n.show()
			
			if self.last_modified != self.xml_parser.modified:
				self.last_modified = self.xml_parser.modified
				if self.onNewMail:
					copy = threading.local()
					copy.show = show
					self.lock.release ()
					self.onNewMail (self.onNewMailArgs, copy.show)
				else:
					self.lock.release ()
			else:
				self.last_modified = self.xml_parser.modified
				self.lock.release ()
			
			return True
		
		except urllib2.URLError as inst:
			# This is almost certainly a transient error, likely due to a lost connection, we don't really care
			# we'll just try to update again in a minute and keep polling until we can actually connect again.
			self.logger.info ("urllib Error: " + str(inst) + " (ignored)")
			self.lock.release ()
			return False

	def u(self, update):
		if update == True:
			if self.refreshInfo () == False:
				raise self.ConnectionError
			return True
		if (time () - self.last_update) > self.timeout:
			if update == False:
				return False
			return self.refreshInfo ()
		return True

	def isConnected(self, update=None):
		"""Call this method to establish if the gConn object believes itself to be connected. This is currently
		defined by having valid data within the last self.timeout seconds. Alternatively, set update=True to force an
		immediate connection validation, even if it has previously connected once in the last self.timeout seconds
		
		Note, calling this with update=True will raise a GmailConn.ConnectionError if the connection fails"""
		return self.u (update)

	def getModificationTime(self, update=None):
		"""Returns the timestamp ( as a float analogous to time.time() ) from the RSS feed when the feed was last updated.
		This is an appropriate (best) way to poll if there are any new messages"""
		self.u (update)
		return self.xml_parser.modified

	def getUnreadMessageCount(self, update=None):
		"""Returns the number of unread messages in the gmail inbox"""
		self.u (update)
		if self.xml_parser.email_count != len(self.xml_parser.emails):
			self.logger.debug ("email_count: " + str (self.xml_parser.email_count))
			self.logger.debug ("len(emails): " + str (len (self.xml_parser.emails)))
			raise self.ParseError ("email_count did not match len(emails)")
		return self.xml_parser.email_count

	def getNewestEmail(self, update=None):
		"""Returns the newest available email"""
		self.u (update)
		if self.getUnreadMessageCount () == 0:
			return None
		else:
			return self.xml_parser.emails[-1].dict()

	def getAllEmails(self, update=None, limit=10):
		"""Returns all unread messages, note the 'limit' parameter, which may be disabled by setting it < 0"""
		self.u (update)
		ret = list()
		cnt = 0
		for email in self.xml_parser.emails:
			if (cnt >= limit) and (limit > 0):
				break
			ret.append(email.dict())
			cnt += 1
		return ret
