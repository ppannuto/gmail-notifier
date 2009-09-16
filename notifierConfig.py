import gtk

class NotifierConfigWindow:

	def __init__(self, username=None, password=None):
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
		if username:
			self.username_entry.set_text (username)
		self.table.attach (self.username_label, 0, 1, 0, 1, xpadding=2, ypadding=2)
		self.table.attach (self.username_entry, 1, 2, 0, 1, xpadding=2, ypadding=2)
		self.username_label.show ()
		self.username_entry.show ()

		self.password_label = gtk.Label ('password')
		self.password_entry = gtk.Entry ()
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

		# Show everything
		self.table.show ()
		self.hbox.show ()
		self.vbox.show ()

		self.window.show()

		# BAM!
		gtk.main()

	def onToggle(self, widget, user_params=None):
		if widget.get_active ():
			self.password_entry.set_visibility (True)
		else:
			self.password_entry.set_visibility (False)

	def onDelete(self, widget, user_params=None):
		gtk.main_quit ()
		self.window.hide ()
		return True

	def onClose(self, widget, user_params=None):
		self.username = self.username_entry.get_text ()
		self.password = self.password_entry.get_text ()

		if self.username == '' or self.password == '':
			dialog = gtk.MessageDialog (buttons=gtk.BUTTONS_OK, type=gtk.MESSAGE_ERROR)
			dialog.set_position (gtk.WIN_POS_CENTER)
			dialog.set_markup ('Both username and password are required!')
			dialog.run ()
			dialog.destroy ()
			return False

		self.onDelete (widget, user_params)

	def onCancel(self, widget, user_params=None):
		self.onDelete (widget, user_params)
