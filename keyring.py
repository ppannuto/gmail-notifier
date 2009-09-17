# Copies of this are all over this internet, the file from at least
# http://www.rittau.org/blog/20070726-01 by Sebastian Rittau
# http://gmazzola.com/notes/Gnome_Keyring_Python.html by Gregory Mazzola
#
# Modified by Pat Pannuto

__version__ = "$Revision: 14294 $"

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

	def get_credentials(self):
		attrs = {"server": self._server, "protocol": self._protocol}
		items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
		return (items[0].attributes["user"], items[0].secret)

	def set_credentials(self, (user, pw)):
		attrs = {
				"user": user,
				"server": self._server,
				"protocol": self._protocol,
				}
		gkey.item_create_sync(gkey.get_default_keyring_sync(),
				gkey.ITEM_NETWORK_PASSWORD, self._name, attrs, pw, True)

	def delete_credentials(self, (user, pw)):
		attrs = {
				"user":user,
				"server":self._server,
				"protocol":self._protocol,
				}
		items = gkey.find_items_sync(gkey.ITEM_NETWORK_PASSWORD, attrs)
		for item in items:
			gkey.item_delete_sync(None, item.item_id)
