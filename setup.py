#!/usr/bin/python

from distutils.core import setup
import glob

setup (
		name='Gmail Notifier',
		version='1.0',
		author='Pat Pannuto',
		author_email='pat.pannuto@gmail.com',
		maintainer='Pat Pannuto',
		maintainer_email='pat.ppannuto@gmail.com',
		url='http://www-personal.umich.edu/~ppannuto/code/index.html',
		description='A notification daemon for any number of GMail inboxes',
		long_description="""
 Gmail Notifier is a simple notifier program written in python, targeting
 (read: tested on) ubuntu, but it should be platform independent.
 .
 Gmail Notifier includes the following features:
    * Multiple account support
    * Secure password storage via gnome-keyring
    * Power Management (reduce or disable polling on battery to reduce
      wifi radio wake-ups)
    * Leverages libnotify for consistent notifications
    * "Stale" mail; distinguishes between emails left unread for a long
      period of time and truly new mail
 .
 Gmail Notifier currently only supports GNOME, but that is only a weakness
 of the password storage model (currently gnome-keyring); expect KDE support
 in an upcoming version
 """,
		download_url='http://www-personal.umich.edu/~ppannuto/code/index.html',
		license='GPL v3',
		scripts = ['gmail-notifier'],
		data_files = [
			('share/applications', ['extra/gmail-notifier.desktop']),
			('share/man/man1', ['extra/gmail-notifier.1']),
			('share/icons/hicolor/scalable/apps', ['icons/nomail.svg']),
			('lib/gmail-notifier', ['gmailLib.py', 'gmailStatusIcon.py', 'keyring.py', 'notifierConfig.py']),
			('lib/gmail-notifier/icons', glob.glob ('icons/*.png')),
			]
		)
