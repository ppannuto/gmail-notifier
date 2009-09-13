#!/usr/bin/python
# -*- coding: utf-8 -*-

# gmailLib 0.1 by Pat Pannuto <pat.pannuto@gmail.com>
# based on gmailatom 0.0.1 by Juan Grande <juan.grande@gmail.com>

from xml import sax
from xml.sax import saxutils
from xml.sax import make_parser
from xml.sax import ContentHandler
from xml.sax.handler import feature_namespaces
from xml.utils.iso8601 import parse as parse_time
import urllib2

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
			print "Scoping error? Name: " + name + ", Last: " + last
			print "self.emails:",self.emails
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
	Instantiate a GmailConn object: gConn = GmailConn (username="username@gmail.com", password="password", proxy=None)

	The object is 'self-updating'.  That is to say, if you request any information (e.g. gConn.getUnreadMessageCount) and
	the cached information is more than 60 seconds out of date, it will query automatically and update.  You may also pass
	the optional 'update=True' parameter to any method to force it to update before returning.
	"""

	realm = "New mail feed"
	host = "https://mail.google.com"
	url = host + "/mail/feed/atom"

	last_update = 0

	class Error(Exception):
		"""Base class for exceptions in this module"""
		pass

	class UnrecoverableError(Error):
		"""This error is currently unused, but is a placeholder for an unrecoverable error in the library"""
		pass

	class ParseError(Error):
		"""The library had some type of trouble parsing the xml feed.  This is likely a transient error, however
		if it persists, it may indicate that google changed the structure of their feed, and the code needs to be updated

		Attributes:
			message -- A string providing more detail of the error
		"""

		def __init__(self, message):
			self.message = message

	def __init__(self, username, password, proxy=None):
		# Add @gmail.com if the caller didn't
		if (username.rfind("@gmail.com")) == -1:
			username += "@gmail.com"
			print "Did not get FQ email address, using", username
		
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
		
#		self.refreshInfo ()
		return

	def sendRequest(self):
		"""Internal -- There is no reason to call this directly"""
		return urllib2.urlopen(self.url)
#		return open('feed.xml', 'r')

	def refreshInfo(self):
		"""Internal -- There is no reason to call this directly"""
		from time import time
		import urllib2
		# get the page and parse it
		try:
			raw_xml = sax.parseString (self.sendRequest().read(), self.xml_parser)
			self.last_update = time ()
#			print "refreshInfo completed successfully at", self.last_update
			return True
		except urllib2.URLError as inst:
			# This is almost certainly a transient error, likely due to a lost connection, we don't really care
			# we'll just try to update again in a minute and keep polling until we can actually connect again.
			print "urllib Error: " + str(inst) + " (ignored)"
			return False

	def isConnected(self, update=False):
		"""Call this method to establish if the gConn object believes itself to be connected. This is currently
		defined by having valid data within the last 60 seconds. Alternatively, set update=True to force an
		immediate connection validation, even if it has previously connected once in the last 60 seconds"""
		from time import time
		if update or (time () - self.last_update > 60):
			return self.refreshInfo ()
		return True

	def getModificationTime(self, update=False):
		"""Returns the timestamp ( as a float analogous to time.time() ) from the RSS feed when the feed was last updated.
		This is an appropriate (best) way to poll if there are any new messages"""
		from time import time
		if update or (time () - self.last_update > 60):
			self.refreshInfo ()
		return self.xml_parser.modified

	def getUnreadMessageCount(self, update=False):
		"""Returns the number of unread messages in the gmail inbox"""
		from time import time
		if update or (time () - self.last_update > 60):
			self.refreshInfo ()
		if self.xml_parser.email_count != len(self.xml_parser.emails):
			print "email_count:",self.xml_parser.email_count
			print "len(emails):",len(self.xml_parser.emails)
			raise ParseError ("email_count did not match len(emails)")
		return self.xml_parser.email_count

	def getNewestEmail(self, update=False):
		"""Returns the newest available email"""
		from time import time
		if update or (time () - self.last_update > 60):
			self.refreshInfo ()
		if self.getUnreadMessageCount () == 0:
			return None
		else:
			return self.xml_parser.emails[-1].dict()

	def getAllEmails(self, update=False, limit=10):
		"""Returns all unread messages, note the 'limit' parameter, which may be disabled by setting it < 0"""
		from time import time
		if update or (time () - self.last_update > 60):
			self.refreshInfo ()
		ret = list()
		cnt = 0
		for email in self.xml_parser.emails:
			if (cnt >= limit) and (limit > 0):
				break
			ret.append(email.dict())
			cnt += 1
		return ret
