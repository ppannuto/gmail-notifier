#!/usr/bin/env python
# Gmail Notifier v2

import logging
logging.basicConfig (level=logging.DEBUG, format="%(asctime)s [%(levelname)s]\t{%(thread)d} %(name)s:%(lineno)d %(message)s")
logger = logging.getLogger ('gmail-notifier2')

APP_NAME = 'gmail-notifier2'

import os
import sys
import gtk
gtk.gdk.threads_init ()
import gobject
gobject.set_application_name(APP_NAME)
import threading
import pynotify
if not pynotify.init ("Gmail Notifier"):
	logger.critical ("Error loading pynotify, dying...")
	raise Exception
from time import sleep

import keyring
import gmailStatusIcon
import gmailLib
from notifierConfig import NotifierConfig

# GLOBAL
gConns = list ()
gConns_lock = threading.RLock ()
CONF_NAME='gmail-notifier.conf'
config = NotifierConfig ([sys.path[0]+CONF_NAME, os.path.expanduser ('~/.' + CONF_NAME), '/etc/'+CONF_NAME])

def on_update(widget, user_params=None):
	logger.debug ('on_update clicked')
	with gConns_lock:
		logger.debug ('on_update got gConns_lock')
		for gConn in gConns:
			try:
				gConn.update (async=True, force_callbacks=True)
			except gConn.Error:
				pass
	logger.debug ('on_update complete')

def on_tellMe(widget, user_params=None):
	logger.debug ('on_tellMe clicked')
	with gConns_lock:
		for gConn in gConns:
			gConn.notify ()

def on_preferences(widget, user_params=None):
	logger.debug ('on_preferences called')
	threading.Thread (target=preferences, name='prefs_thread').start ()

def on_about(widget, user_params=None):
	logger.debug ('on_about called')
	# Do not need gtk_threads_enter/leave since we're in a callback from a widget
	dialog = gtk.AboutDialog ()
	dialog.set_name ('Gmail Notifier')
	dialog.set_version ('2.0.0')
	dialog.set_comments ('A simple applet to watch for new messages from a GMail account')
	dialog.set_authors ('Pat Pannuto')
	dialog.run ()
	dialog.destroy ()

def on_close(widget, user_params=None):
	exit (0)


def generateTooltip():
	locals = threading.local ()
	locals.tooltip = 'Gmail Notifier'
	locals.newmail = False
	with gConns_lock:
		for gConn in gConns:
			if gConn.isAuthenticationError ():
				locals.tooltip += ('\n' + gConn.getUsername () + ': Authentication Error')
			elif gConn.getUnreadMessageCount (update=False):
				locals.cnt = gConn.getUnreadMessageCount (update=False)
				locals.tooltip += ('\n' + gConn.getUsername () + ': ' + str (locals.cnt) + ' unread message' + ('s','')[locals.cnt == 1])
				locals.newmail = True
			else:
				locals.tooltip += ('\n' + gConn.getUsername () + ': No unread messages')
	return locals.tooltip, locals.newmail



def onUpdate(gConn, status_icon):
	logger.debug ('onUpdate called by ' + gConn.getUsername ())
	locals = threading.local ()
	locals.tooltip, locals.newmail = generateTooltip ()

	gtk.gdk.threads_enter ()
	status_icon.set_tooltip (locals.tooltip)
	if locals.newmail:
		status_icon.set_from_file (gmailStatusIcon.TRAY_NEWMAIL)
	else:
		status_icon.set_from_file (gmailStatusIcon.TRAY_NOMAIL)
	gtk.gdk.threads_leave ()

def onDisconnect(gConn, status_icon):
	logger.debug ('onDisconnect called by ' + gConn.getUsername ())
	gtk.gdk.threads_enter ()
	status_icon.set_from_file (gmailStatusIcon.TRAY_NOCONN)
	status_icon.set_tooltip ('Gmail Notifier -- Not Connected')
	gtk.gdk.threads_leave ()

def onAuthenticationError(gConn, status_icon):
	logger.debug ('onAuthenticationError called by ' + gConn.getUsername ())
	locals = threading.local ()
	(locals.tooltip, locals.newmail) = generateTooltip ()

	gtk.gdk.threads_enter ()
	status_icon.set_from_file (gmailStatusIcon.TRAY_AUTHERR)
	status_icon.set_tooltip (locals.tooltip)
	gtk.gdk.threads_leave ()
	logger.debug ('onAuthenticationError updated status_icon')

	locals.n = pynotify.Notification ('Authentication Error!', gConn.getUsername () + ' failed to authenticate')
	locals.n.show ()

def onPowerChange(args, kwargs):
	print 'power change'
	print '  args: ' + str(args)
	print 'kwargs: ' + str(kwargs)


def PowerThread(dev, gConns):
	from time import sleep
	while True:
		for gConn in gConns:
			if dev.GetProperty ('ac_adapter.present'):
				logger.debug ('POWER: ac adapter present')
				gConn.set_frequency ()
			else:
				logger.debug ('POWER: on battery')
				gConn.set_frequency (60)
		sleep (60)


def preferences(gConn=None):
	logger.debug ('preferences called')
	if gConn:
		gConn.configure (config.config)
	else:
		config.showConfigWindow (gConns, gConns_lock)



def main():

	#Set up the status icon (tray icon)
	gtk.gdk.threads_enter ()
	status_icon = gmailStatusIcon.GmailStatusIcon (on_update, on_tellMe, on_preferences, on_about, on_close, args=gConns)
	gtk.gdk.threads_leave ()
	logger.debug ('status icon initialized')

	#Create gConn objects for each username
	for username in config.get_usernames ():
		logger.debug ('Creating gConn for ' + username)
		gConns.append (gmailLib.GmailConn (
			username, 
			config.get_password (username),
			frequency=config.get_ac_polling (username),
			logLevel=logging.DEBUG)
			)

	#Create and start a gConn object to communicate with GMail
	with gConns_lock:
		for gConn in gConns:
			gConn.set_onUpdate (onUpdate, status_icon)
			gConn.set_onDisconnect (onDisconnect, status_icon)
			gConn.set_onAuthenticationError (onAuthenticationError, status_icon)
			gConn.start ()

	#If there's no usernames in the config file, open the preferences dialog
	if not config.get_usernames ():
		logger.debug ('No usernames found in config')
		gtk.gdk.threads_enter ()
		dialog = gtk.MessageDialog (buttons=gtk.BUTTONS_OK)
		dialog.set_position (gtk.WIN_POS_CENTER)
		dialog.set_title ('Gmail Notifier')
		dialog.set_markup ('No accounts were found in the configuration file')
		dialog.run ()
		dialog.destroy ()
		gtk.gdk.threads_leave ()
		threading.Thread (target=preferences, name='prefs_thread').start ()

	#Try to hook into dbus so we can monitor power state
	try:
		raise ImportError	# XXX
		import dbus
		from dbus.mainloop.glib import DBusGMainLoop
		from dbus.mainloop.glib import threads_init as dbus_threads_init
		dbus_threads_init ()
		DBusGMainLoop (set_as_default=True)

		bus = dbus.SystemBus ()
		hal_obj = bus.get_object ('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
		hal = dbus.Interface (hal_obj, 'org.freedesktop.Hal.Manager')
		
		dev_obj = bus.get_object ("org.freedesktop.Hal", hal.FindDeviceByCapability ("ac_adapter")[0])
		dev = dbus.Interface (dev_obj, "org.freedesktop.Hal.Device")
		dev.connect_to_signal ("PropertyModified", onPowerChange)

		threading.Thread (target=PowerThread, name='PowerThread', args=(dev, gConns)).start ()
	except ImportError:
		pass

	gtk.gdk.threads_enter ()
	gtk.main ()
	gtk.gdk.threads_leave ()

if __name__ == '__main__':
	main ()
