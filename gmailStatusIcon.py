# This file is part of gmail-notifier.
# 
#     gmail-notifier is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
# 
#     gmail-notifier is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     You should have received a copy of the GNU General Public License
#     along with gmail-notifier.  If not, see <http://www.gnu.org/licenses/>.
# 
# 
# Copyright 2009 by Pat Pannuto <pat.pannuto@gmail.com>

import gtk

TRAY_NOCONN = 'noconnection.png'
TRAY_NOMAIL = 'nomail.png'
TRAY_NEWMAIL = 'newmail.png'
TRAY_AUTHERR = 'autherr.png'
TRAY_UPDATING = 'updating.png'
TRAY_OLDMAIL = 'oldmail.png'

class GmailStatusIcon(gtk.StatusIcon):

	TRAY_NOCONN = TRAY_NOCONN
	TRAY_NOMAIL = TRAY_NOMAIL
	TRAY_NEWMAIL = TRAY_NEWMAIL
	TRAY_AUTHERR = TRAY_AUTHERR
	TRAY_UPDATING = TRAY_UPDATING
	TRAY_OLDMAIL = TRAY_OLDMAIL

	def __init__(self, on_update, on_tellMe, on_preferences, on_about, on_close, _=lambda s:s):
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
				('Update', gtk.STOCK_REFRESH, _('_Update now'), None, 'Force an immediate refresh', on_update),
				('TellMe', None, _('_Tell me again'), None, 'Repeat the last notification', on_tellMe),
				('Inbox', None, _('Go to my _Inbox...'), None, 'Open your inbox in the default browser', self.on_inbox),
				('Preferences', gtk.STOCK_PREFERENCES, _('_Preferences...'), None, 'Configure GmailNotifier2', on_preferences),
				('About', gtk.STOCK_ABOUT, _('_About...'), None, 'About GmailNotifier2', on_about),
				('Close', gtk.STOCK_CLOSE, _('_Close'), None, 'Exit GmailNotifier2', on_close)
			  ]

		ag = gtk.ActionGroup ('Gmail Notifier Actions')
		ag.add_actions (actions, user_data=self)
		self.manager = gtk.UIManager ()
		self.manager.insert_action_group (ag, 0)
		self.manager.add_ui_from_string (menu)
		self.menu = self.manager.get_widget ('/Menubar/Menu/About').props.parent
		self.set_from_file (self.TRAY_NOCONN)
		self.set_tooltip (_('Gmail Notifier') + '\n' + _('Not Connected'))
		self.set_visible (True)
		self.connect ('activate', self.on_icon_click)
		self.connect ('popup-menu', self.on_popup_menu)

	def on_inbox(self, data):
		try:
			import webbrowser
		except ImportError:
			return
		try:
			webbrowser.open('http://mail.google.com')
		except webbrowser.Error:
			return

	def on_icon_click(self, data):
		try:
			import webbrowser
		except ImportError:
			return
		try:
			webbrowser.open('http://mail.google.com')
		except webbrowser.Error:
			return

	def on_popup_menu(self, status, button, time):
		self.menu.popup (None, None, None, button, time)
