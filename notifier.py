#!/usr/bin/env python
# Gmail Notifier v2

import logging
logging.basicConfig (level=logging.DEBUG, format="%(asctime)s [%(levelname)s]\t{%(thread)d} %(name)s:%(lineno)d %(message)s")
logger = logging.getLogger ('notifier')

APP_NAME = 'gmail-notifier'

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
gConns = dict ()
gConns_lock = threading.RLock ()
CONF_NAME='gmail-notifier.conf'
config = NotifierConfig ([sys.path[0]+CONF_NAME, os.path.expanduser ('~/.' + CONF_NAME), '/etc/'+CONF_NAME])
config_lock = threading.RLock ()
prefs_lock = threading.Lock ()

#####################
# Utility Functions #
#####################

def updateTooltip(status_icon, gtk_locked=False):
	locals = threading.local ()
	locals.tooltip = 'Gmail Notifier'
	locals.newmail = False
	locals.authErr = False
	locals.noConn = False
	with gConns_lock:
		if len (gConns) == 0:
			locals.tooltip += ('\nNo accounts configured')
			locals.noConn = True
		else:
			for gConn in gConns.values ():
				if gConn.isAuthenticationError ():
					locals.authErr = True
					locals.tooltip += ('\n' + gConn.getUsername () + ': Authentication Error')
				elif gConn.getUnreadMessageCount (update=False):
					locals.newmail = True
					locals.cnt = gConn.getUnreadMessageCount (update=False)
					locals.tooltip += ('\n' + gConn.getUsername () + ': ' + str (locals.cnt) + ' unread message' + ('s','')[locals.cnt == 1])
				elif not gConn.isConnected (update=False):
					# There is a _very_ small window before one of onUpdate,onAuthenticationError,onDisconnect has been called
					locals.tooltip += ('\n' + gConn.getUsername () + ': Connecting...')
				else:
					locals.tooltip += ('\n' + gConn.getUsername () + ': No unread messages')

	if not gtk_locked:
		gtk.gdk.threads_enter ()
	status_icon.set_tooltip (locals.tooltip)
	if locals.noConn:
		status_icon.set_from_file (status_icon.TRAY_NOCONN)
	elif locals.authErr:
		status_icon.set_from_file (status_icon.TRAY_AUTHERR)
	elif locals.newmail:
		status_icon.set_from_file (status_icon.TRAY_NEWMAIL)
	else:
		status_icon.set_from_file (status_icon.TRAY_NOMAIL)
	if not gtk_locked:
		gtk.gdk.threads_leave ()


def preferences(gConn=None):
	# Utility thread to spawn preferences in a separate window / thread
	logger.debug ('preferences called')
	# XXX: ugly
	if prefs_lock.locked (): # Why do Lock's not provide blocking=0 like RLock's?
		logger.debug ('do not allow multiple instances of preferences at once')
	else:
		prefs_lock.acquire ()

	with config_lock:
		if gConn:
			gConn.configure (config)
		else:
			config.showConfigWindow (gConns, gConns_lock)
			onPowerChange (None, None)

	prefs_lock.release ()


##############################
# Callbacks from status_icon #
##############################

def on_update(widget, user_params=None):
	logger.debug ('on_update clicked')
	with gConns_lock:
		logger.debug ('on_update got gConns_lock')
		for gConn in gConns.values ():
			try:
				gConn.update (async=True, force_callbacks=True)
			except gConn.Error:
				pass
	logger.debug ('on_update complete')

def on_tellMe(widget, user_params=None):
	logger.debug ('on_tellMe clicked')
	with gConns_lock:
		for gConn in gConns.values ():
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

###################
# gConn callbacks #
###################

def onUpdate(gConn, status_icon):
	logger.debug ('onUpdate called by ' + gConn.getUsername ())
	updateTooltip (status_icon)

def onDisconnect(gConn, status_icon):
	logger.debug ('onDisconnect called by ' + gConn.getUsername ())
	gtk.gdk.threads_enter ()
	status_icon.set_from_file (status_icon.TRAY_NOCONN)
	status_icon.set_tooltip ('Gmail Notifier -- Not Connected')
	gtk.gdk.threads_leave ()

def onAuthenticationError(gConn, status_icon):
	logger.debug ('onAuthenticationError called by ' + gConn.getUsername ())
	locals = threading.local ()

	updateTooltip (status_icon)

	locals.n = pynotify.Notification ('Authentication Error!', gConn.getUsername () + ' failed to authenticate')
	locals.n.show ()


##################
# dbus callbacks #
##################

def onPowerChange(args, kwargs):
	with gConns_lock:
		for gConn in gConns.values ():
			if dev.GetProperty ('ac_adapter.present'):
				logger.debug ('POWER: ac adapter present - ' + str(args))
				gConn.set_power (ac=True)
			else:
				logger.debug ('POWER: on battery - ' + str(args))
				gConn.set_power (ac=False)

##########################
# gConn config callbacks #
##########################

def onNewGConn(gConn, status_icon):
	# Already have gtk.gdk.threads () and gConns_lock
	gConn.set_onUpdate (onUpdate, status_icon)
	gConn.set_onDisconnect (onDisconnect, status_icon)
	gConn.set_onAuthenticationError (onAuthenticationError, status_icon)
	gConn.start ()
	updateTooltip (status_icon, gtk_locked=True)

def onDeleteGConn(gConn, status_icon):
	updateTooltip (status_icon, gtk_locked=True)


########
# Main #
########

def main():

	#Set up the status icon (tray icon)
	gtk.gdk.threads_enter ()
	status_icon = gmailStatusIcon.GmailStatusIcon (on_update, on_tellMe, on_preferences, on_about, on_close, args=gConns)
	gtk.gdk.threads_leave ()
	config.set_onNewGConn (onNewGConn, status_icon)
	config.set_onDeleteGConn (onDeleteGConn, status_icon)
	logger.debug ('status icon initialized')

	#Create gConn objects for each username
	for username in config.get_usernames ():
		logger.debug ('Creating gConn for ' + username)
		gConns.update (
				{username:
				gmailLib.GmailConn (
					username,
					config=config,
					logLevel=logging.DEBUG
					)
				})

	#Create and start a gConn object to communicate with GMail
	with gConns_lock:
		for gConn in gConns.values ():
			onNewGConn (gConn, status_icon)

	#If there's no usernames in the config file, open the preferences dialog
	with config_lock:
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
		# XXX: WHAT? So, I can't find information on how to pass arguments to dbus callbacks, including
		# the dbus device object itself -- so it's global for now, which is UGLY. Ugh...
		#
		# While we're at annoying design phenomeona, I would like to put all of this into gConn, but
		# the object doesn't have a native mainloop (nor does it require one to operate), so it does
		# not seem logical to place it there. I think this is currently a weakness of the python dbus
		# interface, but not a critical issue I suppose
		#
		# The result of this is that onPowerChange should be called once every time a new gConn object
		# is created so that is has the correct power state. Ugly, but effective
		import dbus
		from dbus.mainloop.glib import DBusGMainLoop
		from dbus.mainloop.glib import threads_init as dbus_threads_init
		dbus_threads_init ()
		DBusGMainLoop (set_as_default=True)

		bus = dbus.SystemBus ()
		hal_obj = bus.get_object ('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
		hal = dbus.Interface (hal_obj, 'org.freedesktop.Hal.Manager')
		
		dev_obj = bus.get_object ("org.freedesktop.Hal", hal.FindDeviceByCapability ("ac_adapter")[0])
		global dev
		dev = dbus.Interface (dev_obj, "org.freedesktop.Hal.Device")
		dev.connect_to_signal ("PropertyModified", onPowerChange)
		
		onPowerChange (None, None)
	except ImportError:
		pass

	updateTooltip (status_icon)

	gtk.gdk.threads_enter ()
	gtk.main ()
	gtk.gdk.threads_leave ()

if __name__ == '__main__':
	main ()
