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

import gnomekeyring as gkey

class Keyring(object):
	def __init__(self, name, server, protocol, setName=False):
		if setName:
			import gobject
			gobject.set_application_name (name)
		self._name = name
		self._server = server
		self._protocol = protocol
		self._keyring = gkey.get_default_keyring_sync()

	def has_credentials(self):
		try:
			attrs = {"server": self._server, "protocol": self._protocol}
			items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
			return len(items) > 0
		except gkey.DeniedError:
			return False
		except gkey.NoMatchError:
			return False

	def get_credentials(self, user):
		attrs = {"server": self._server, "protocol": self._protocol}
		try:
			items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
			for item in items:
				if item.attributes["user"] == user:
					return item.secret
		except gkey.NoMatchError:
			pass
		return None

	def set_credentials(self, user, pw):
		attrs = {
				"user": user,
				"server": self._server,
				"protocol": self._protocol,
				}
		gkey.item_create_sync(gkey.get_default_keyring_sync(),
				gkey.ITEM_NETWORK_PASSWORD, self._name, attrs, pw, True)

	def delete_credentials(self, user, pw=None):
		attrs = {
				"user":user,
				"server":self._server,
				"protocol":self._protocol,
				}
		items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
		for item in items:
			gkey.item_delete_sync(None, item.item_id)
