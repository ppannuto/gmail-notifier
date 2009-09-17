#!/usr/bin/env python
# Gmail Notifier v2

import logging
logging.basicConfig (level=logging.DEBUG, format="%(asctime)s [%(levelname)s]\t{%(thread)d} %(name)s:%(lineno)d %(message)s")
logger = logging.getLogger ('gmail-notifier2')

APP_NAME = 'gmail-notifier2'

import gtk
import gobject
gobject.set_application_name(APP_NAME)
import threading
import pynotify
if not pynotify.init ("Gmail Notifier 2"):
	logger.critical ("Error loading pynotify, dying...")
	raise Exception
from time import sleep

import keyring
import gmailStatusIcon
import gmailLib
import notifierConfig

def on_update(entry, gConn):
	logger.debug ('on_update clicked')
	try:
		gConn.isConnected (update=True)
	except gConn.Error:
		pass

def on_tellMe(entry, gConn):
	logger.debug ('on_tellMe clicked')
	gConn.notify ()

def on_preferences(entry=None, gConn=None):
	logger.debug ('on_preferences called')
	preferences (entry=entry, gConn=gConn, gtk_locked=True)

def on_about(entry, user_params=None):
	logger.debug ('on_about called')
	dialog = gtk.AboutDialog ()
	dialog.set_name ('Gmail Notifier')
	dialog.set_version ('2.0.0')
	dialog.set_comments ('A simple applet to watch for new messages from a GMail account')
	dialog.set_authors ('Pat Pannuto')
	dialog.run ()
	dialog.destroy ()

def on_close(entry, user_params=None):
	exit (0)


def onNewMail(status_icon, emails, gConn):
	logger.debug ('onNewMail called')
	gtk.gdk.threads_enter ()
	if gConn.getUnreadMessageCount (update=False):
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

def onAuthenticationError(status_icon, gConn):
	logger.debug ('onAuthenticationError called')
	gtk.gdk.threads_enter ()
	status_icon.set_from_file (gmailStatusIcon.TRAY_AUTHERR)
	status_icon.set_tooltip ('Gmail Notifier -- Authentication Error')
	dialog = gtk.MessageDialog (buttons=gtk.BUTTONS_OK, type=gtk.MESSAGE_ERROR)
	dialog.set_position (gtk.WIN_POS_CENTER)
	dialog.set_title ('GmailNotifier2 Error')
	dialog.set_markup ('Authentication error!\n\nBad username or password')
	dialog.run ()
	dialog.destroy ()
	gtk.gdk.threads_leave ()
	preferences (gConn=gConn)


def preferences_thread(entry=None, gConn=None, gtk_locked=False):
	logger.debug ('preferences called (gConn: ' + str(gConn) + ')')
	Keyring = keyring.Keyring ('gmail-notifier2', 'mail.google.com', 'https')

	if Keyring.has_credentials ():
		username, password = Keyring.get_credentials ()
		logger.debug ('preferences: old credentials: ' + username + '/PASSWORD')
		if not gtk_locked:
			gtk.gdk.threads_enter ()
		config = notifierConfig.NotifierConfigWindow (username, password, log_level=logging.DEBUG)
		if not gtk_locked:
			gtk.gdk.threads_leave ()
	else:
		logger.debug ('preferences: no old credentials')
		if not gtk_locked:
			gtk.gdk.threads_enter ()
		config = notifierConfig.NotifierConfigWindow (log_level=logging.DEBUG)
		if not gtk_locked:
			gtk.gdk.threads_leave ()

	config.wait ()
	if config.username == '' or config.password == '':
		logger.debug ('preferences: empty username or password field (likely cancelled)')
	else:
		logger.debug ('Got new credentials: ' + config.username + '/PASSWORD')
		Keyring.delete_credentials ((username, password))
		Keyring.set_credentials ((config.username, config.password))
		if gConn:
			logger.debug ('preferences attempting to reset credentials')
			gConn.resetCredentials (config.username, config.password)

def preferences(entry=None, gConn=None, gtk_locked=False):
	threading.Thread (target=preferences_thread, args=(entry, gConn, gtk_locked)).start ()

def main():
	gtk.gdk.threads_init ()

	#Load username,password from the keyring; spawn configuraion window if it isn't set
	Keyring = keyring.Keyring (APP_NAME, 'mail.google.com', 'https')
	if not Keyring.has_credentials ():
		preferences ()
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
	gtk.gdk.threads_enter ()
	status_icon = gmailStatusIcon.GmailStatusIcon (on_update, on_tellMe, on_preferences, on_about, on_close, args=gConn)
	gtk.gdk.threads_leave ()
	logger.debug ('status icon initialized')

	gConn.set_onNewMail (onNewMail, status_icon)
	gConn.set_onDisconnect (onDisconnect, status_icon)
	gConn.set_onAuthenticationError (onAuthenticationError, status_icon)
	gConn.start ()
	logger.debug ('gConn start()ed')

	gtk.gdk.threads_enter ()
	gtk.main ()
	gtk.gdk.threads_leave ()

if __name__ == '__main__':
	main ()
