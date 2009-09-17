import gtk
import logging
import threading

class NotifierConfigWindow:

	def __init__(self, username=None, password=None, log_level=logging.WARNING):
		# Set up logging
		logging.basicConfig (level=log_level, format="%(asctime)s [%(levelname)s]\t{%(thread)s} %(name)s:%(lineno)d %(message)s")
		self.logger = logging.getLogger ('configWindow')
		self.logger.debug ('starting NotifierConfigWindow')

		# Copy in default arguments
		self.username = username
		self.password = password

		# Set up a main window
		self.window = gtk.Window (gtk.WINDOW_TOPLEVEL)
		self.window.set_title ('Gmail Notifier Preferences')
		self.window.set_position (gtk.WIN_POS_CENTER)
		self.window.set_modal (True)

		# Register events
		self.window.connect ('delete_event', self.onDelete)

		# Create a table for window
		self.table = gtk.Table (rows=2, columns=2)

		# Create and attach widgets for username/password
		self.username_label = gtk.Label ('username')
		self.username_entry = gtk.Entry ()
		self.username_entry.connect ('activate', self.onClose)
		if username:
			self.username_entry.set_text (username)
		self.table.attach (self.username_label, 0, 1, 0, 1, xpadding=2, ypadding=2)
		self.table.attach (self.username_entry, 1, 2, 0, 1, xpadding=2, ypadding=2)
		self.username_label.show ()
		self.username_entry.show ()

		self.password_label = gtk.Label ('password')
		self.password_entry = gtk.Entry ()
		self.password_entry.connect ('activate', self.onClose)
		self.password_entry.set_visibility (False)
		if password:
			self.password_entry.set_text (password)
		self.table.attach (self.password_label, 0, 1, 1, 2, xpadding=2, ypadding=2)
		self.table.attach (self.password_entry, 1, 2, 1, 2, xpadding=2, ypadding=2)
		self.password_label.show()
		self.password_entry.show()

		self.show_password_checkbutton = gtk.CheckButton ('Show Password')
		self.show_password_checkbutton.active = False
		self.show_password_checkbutton.connect ('toggled', self.onToggle)
		self.table.attach (self.show_password_checkbutton, 1, 2, 2, 3, xpadding=2, ypadding=2)
		self.show_password_checkbutton.show()

		# Create an hbox to hold Cancel/Close buttons
		self.hbox = gtk.HBox ()

		self.cancel_button = gtk.Button (stock=gtk.STOCK_CANCEL)
		self.hbox.pack_start (self.cancel_button)
		self.cancel_button.connect ('clicked', self.onCancel)
		self.cancel_button.show ()

		self.close_button = gtk.Button (stock=gtk.STOCK_CLOSE)
		self.hbox.pack_start (self.close_button)
		self.close_button.connect ('clicked', self.onClose)
		self.close_button.show ()

		# Create a vbox to hold the table/hbox
		self.vbox = gtk.VBox ()
		self.vbox.pack_start (self.table, padding=10)
		self.vbox.pack_start (self.hbox)

		# Add top container to window
		self.window.add (self.vbox)

		# Have an event for window destruction
		self.destroy_event = threading.Event ()
#		self.window.connect ('destroy-event', self.onDestroy)

		# Show everything
		self.table.show ()
		self.hbox.show ()
		self.vbox.show ()

		self.window.show()
		
		self.logger.debug ('NotifierConfigWindow __init__ complete')

	def onToggle(self, widget, user_params=None):
		if widget.get_active ():
			self.password_entry.set_visibility (True)
		else:
			self.password_entry.set_visibility (False)

	def onDelete(self, widget, user_params=None):
		self.window.destroy ()
		self.destroy_event.set ()

	def onClose(self, widget, user_params=None):
		self.username = self.username_entry.get_text ()
		self.password = self.password_entry.get_text ()

		if self.username == '' or self.password == '':
			gtk.gdk.threads_enter ()
			dialog = gtk.MessageDialog (buttons=gtk.BUTTONS_OK, type=gtk.MESSAGE_ERROR)
			dialog.set_position (gtk.WIN_POS_CENTER)
			dialog.set_markup ('Error!\n\nBoth username and password are required!')
			dialog.run ()
			dialog.destroy ()
			gtk.gdk.threads_leave ()
			return False

		self.onDelete (widget, user_params)

	def onCancel(self, widget, user_params=None):
		self.username = ''
		self.password = ''
		self.onDelete (widget, user_params)

	def onDestroy(self, widget, user_params=None):
		self.destroy_event.set ()

	def wait(self, timeout=None):
		self.destroy_event.wait (timeout=timeout)
