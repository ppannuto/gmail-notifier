#!/usr/bin/env python
# Gmail Notifier v2

import logging
logging.basicConfig (level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s")
logger = logging.getLogger ('gmail-notifier2')

import gtk
import threading
import pynotify
if not pynotify.init ("Gmail Notifier 2"):
	logger.critical ("Error loading pynotify, dying...")
	raise Exception
from time import sleep

import keyring
import gmailStatusIcon
import gmailLib

def onNewMail(status_icon, emails, gConn):
	logger.debug ('onNewMail called')
	gtk.gdk.threads_enter ()
	if len (emails):
		status_icon.set_from_file (gmailStatusIcon.TRAY_NEWMAIL)
		cnt = gConn.getUnreadMessageCount (update=False)
		status_icon.set_tooltip ('Gmail Notifier -- You have ' + str (cnt) + ' unread message' + ('s','')[cnt == 1])
	else:
		status_icon.set_from_file (gmailStatusIcon.TRAY_NOMAIL)
		status_icon.set_tooltip ('Gmail Notifier -- You have no unread messages')
	gtk.gdk.threads_leave ()

def onDisconnect(status_icon):
	logger.debug ('onDisconnect called')
	gtk.gdk.threads_enter ()
	status_icon.set_from_file (gmailStatusIcon.TRAY_NOCONN)
	status_icon.set_tooltip ('Gmail Notifier -- Not Connected')
	gtk.gdk.threads_leave ()

def on_update(data, gConn):
	logger.debug ('on_update clicked')
	try:
		gConn.isConnected (update=True)
	except gConn.Error:
		pass

def on_tellMe(data, gConn):
	logger.debug ('on_tellMe clicked')
	gConn.notify ()

def on_preferences(data):
	from gnomekeyring import NoMatchError

	def responseToDialog(entry, dialog, response):
		print "RESPONSE"
		dialog.response(response)
		dialog.destroy()

	if (data):
		Keyring = data
	else:
		Keyring = keyring.Keyring ('gmail-notifier2', 'mail.google.com', 'https')

	try:
		raise NoMatchError
		username, password = Keyring.get_credentials ()
	except NoMatchError:
		username = None
		password = None
	
	dialog = gtk.Dialog ("Gmail Notifier2 Preferences", None, gtk.DIALOG_MODAL, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

	username_entry = gtk.Entry ()
	password_entry = gtk.Entry ()
	password_entry.set_visibility(False)
	try:
		username_entry.set_text (username)
		password_entry.set_text (password)
	except TypeError:
		pass
	username_entry.connect ("activate", responseToDialog, dialog, gtk.RESPONSE_CLOSE)
	password_entry.connect ("activate", responseToDialog, dialog, gtk.RESPONSE_CLOSE)

	username_hbox = gtk.HBox ()
	username_hbox.pack_start (gtk.Label("Username:"), False, 5, 5)
	username_hbox.pack_end (username_entry)
	password_hbox = gtk.HBox ()
	password_hbox.pack_start (gtk.Label("Password:"), False, 5, 5)
	password_hbox.pack_end (password_entry)

	dialog.vbox.pack_start (gtk.Label("Enter your gmail username and password"), True, True, 10)
	dialog.vbox.pack_start (username_hbox, True, True, 5)
	dialog.vbox.pack_start (password_hbox, True, True, 5)
	dialog.show_all()

	dialog.run()
	username = username_entry.get_text()
	password = password_entry.get_text()
	print "Got username >>>" + username + "<<< and password >>>" + password + "<<<"
	if password == "":
		print "This is the bug I haven't been able to fix, just try it again..."
		raise Exception
	print 'a'
	dialog.destroy()
	print 'b'
	Keyring.set_credentials ((username, password))
	print 'c'


def on_about(data):
	dialog = gtk.AboutDialog ()
	dialog.set_name ('Gmail Notifier')
	dialog.set_version ('2.0.0')
	dialog.set_comments ('A simple applet to watch for new messages from a GMail account')
	dialog.set_authors ('Pat Pannuto')
	dialog.run ()
	dialog.destroy ()

def on_close(data):
	exit (0)


def main():
	gtk.gdk.threads_init ()

	#Load username,password from the keyring; spawn configuraion window if it isn't set
	Keyring = keyring.Keyring ('gmail-notifier2', 'mail.google.com', 'https')
	if not Keyring.has_credentials ():
		on_preferences (Keyring)
		if not Keyring.has_credentials ():
			logger.critical ("Failed to set credentials")
			raise Exception

	username, password = Keyring.get_credentials ()
	logger.debug ('username (' + username + ') and password (REDACTED) obtained')

	gConn = gmailLib.GmailConn (
			username,
			password,
			logLevel=logging.DEBUG
			)
	logger.debug ('gConn created')

	#Set up the status icon (tray icon)
	status_icon = gmailStatusIcon.GmailStatusIcon (on_update, on_tellMe, on_preferences, on_about, on_close, args=gConn)
	logger.debug ('status icon initialized')

	gConn.set_onNewMail (onNewMail, status_icon)
	gConn.set_onDisconnect (onDisconnect, status_icon)
	gConn.start ()
	logger.debug ('gConn start()ed')

	gtk.main ()

if __name__ == '__main__':
	main ()
