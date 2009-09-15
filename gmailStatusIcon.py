# Based on 'TrackerStatusIcon', found here: http://www.mail-archive.com/tracker-list@gnome.org/msg00669.html
# written by Mikkel Kamstrup Erlandsen

import gtk

TRAY_NOCONN = 'noconnection.png'
TRAY_NOMAIL = 'nomail.png'
TRAY_NEWMAIL = 'newmail.png'

class GmailStatusIcon(gtk.StatusIcon):

	TRAY_NOCONN = TRAY_NOCONN
	TRAY_NOMAIL = TRAY_NOMAIL
	TRAY_NEWMAIL = TRAY_NEWMAIL

	def __init__(self, on_update, on_tellMe, on_preferences, on_about, on_close, args=None):
		gtk.StatusIcon.__init__(self)
		menu = '''
			<ui>
				<menubar name="Menubar">
					<menu action="Menu">
						<menuitem action="Update" />
						<menuitem action="TellMe" />
						<menuitem action="Inbox" />
						<separator />
						<menuitem action="Preferences" />
						<menuitem action="About" />
						<menuitem action="Close" />
					</menu>
				</menubar>
			</ui>
		'''
		actions = [
				('Menu', None, 'Menu'),
				('Update', gtk.STOCK_REFRESH, '_Update now', None, 'Force an immediate refresh', on_update),
				('TellMe', None, '_Tell me again', None, 'Repeat the last notification', on_tellMe),
				('Inbox', None, 'Go to my _Inbox...', None, 'Open your inbox in the default browser', self.on_inbox),
				('Preferences', gtk.STOCK_PREFERENCES, '_Preferences...', None, 'Configure GmailNotifier2', on_preferences),
				('About', gtk.STOCK_ABOUT, '_About...', None, 'About GmailNotifier2', on_about),
				('Close', gtk.STOCK_CLOSE, '_Close', None, 'Exit GmailNotifier2', on_close)
			  ]

		ag = gtk.ActionGroup ('Gmail Notifier Actions')
		ag.add_actions (actions, user_data=args)
		self.manager = gtk.UIManager ()
		self.manager.insert_action_group (ag, 0)
		self.manager.add_ui_from_string (menu)
		self.menu = self.manager.get_widget ('/Menubar/Menu/About').props.parent
		self.set_from_file (self.TRAY_NOCONN)
		self.set_tooltip ('Gmail Notifier -- Not Connected')
		self.set_visible (True)
		self.connect ('activate', self.on_icon_click)
		self.connect ('popup-menu', self.on_popup_menu)

	def on_inbox(self, data):
		import webbrowser
		webbrowser.open('http://mail.google.com')

	def on_icon_click(self, data):
		import webbrowser
		webbrowser.open('http://mail.google.com')

	def on_popup_menu(self, status, button, time):
		self.menu.popup (None, None, None, button, time)
