#!/usr/bin/python
# Gmail Notifier v2

import gtk
import threading
import pynotify
if not pynotify.init ("Gmail Notifier 2"):
	print "Error loading pynotify, dying..."
	raise Exception
from time import sleep

import keyring
import gmailStatusIcon
import gmailLib

def on_update(data):
	print 'update clicked'

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
	dialog.run()
	dialog.destroy()

def on_close(data):
	exit (0)


class UpdateThread(threading.Thread):

	def __init__(self, status_icon, username, password, proxy=None):
		threading.Thread.__init__(self)
		try:
			gtk.gdk.threads_enter ()
			self.status_icon = status_icon
		finally:
			gtk.gdk.threads_leave ()
		self.username = username
		self.password = password
		self.proxy = proxy

	def run(self):
		gC = gmailLib.GmailConn (self.username, self.password, self.proxy)
		print 'gC created successfully'
		last_modification_time = 0

		# A list of all the emails already shown to the user, allows us to only show new emails
		shown = []
		state = 'NOCONN'

		while True:
			last_state = state
			modification_time = gC.getModificationTime ()
			if not gC.isConnected():
				state = 'NOCONN'
			elif last_modification_time != modification_time:
				last_modification_time = modification_time
				
				show = []

				for email in gC.getAllEmails ():
					if email['id'] not in shown:
						show.append(email)
						shown.append(email['id'])

				if len(show) == 0:
					if gC.getUnreadMessageCount () == 0:
						state = 'NOMAIL'
					else:
						state = 'NEWMAIL'
				elif len(show) == 1:
					state = 'NEWMAIL'
					n = pynotify.Notification (email['title'], email['summary'])
					n.show()
				else:
					state = 'NEWMAIL'
					text = "(newest): " + show[0]['title']
					text += '\n\n'
					text += show[0]['summary']
					n = pynotify.Notification ('You have ' + str (gC.getUnreadMessageCount ()) + ' unread messages', text)
					n.show()
			else:
				if gC.getUnreadMessageCount () == 0:
					state = 'NOMAIL'
				else:
					state = 'NEWMAIL'

			if state != last_state:
				try:
					gtk.gdk.threads_enter ()
					if state == 'NOCONN':
						self.status_icon.set_from_file (self.status_icon.TRAY_NOCONN)
					elif state == 'NOMAIL':
						self.status_icon.set_from_file (self.status_icon.TRAY_NOMAIL)
					elif state == 'NEWMAIL':
						self.status_icon.set_from_file (self.status_icon.TRAY_NEWMAIL)
				finally:
					gtk.gdk.threads_leave ()
			sleep (20)


def main():
	gtk.gdk.threads_init()

	#Load username,password from the keyring; spawn configuraion window if it isn't set
	Keyring = keyring.Keyring ('gmail-notifier2', 'mail.google.com', 'https')
	if not Keyring.has_credentials ():
		on_preferences (Keyring)
		if not Keyring.has_credentials ():
			print "Failed to set credentials"
			raise Exception

	print 'd'
	username, password = Keyring.get_credentials ()
	print 'e'

	#Set up the status icon (tray icon)
	status_icon = gmailStatusIcon.GmailStatusIcon(on_update, on_preferences, on_about, on_close)
	print 'f'

	update_thread = UpdateThread (status_icon, username, password)
	update_thread.daemon = True
	update_thread.start()
	print 'g'

	gtk.main()

if __name__ == '__main__':
	main()
