# -*- coding: utf-8 -*-

# Bluemindo: Ergonomic and modern music player designed for audiophiles.
# Copyright (C) 2007-2016  Erwan Briand

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 3 of the License.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository.GObject import idle_add
from gi.repository.Gtk import main_quit as gtk_main_quit
from hashlib import md5 as md5_new
from os.path import join, isfile, isdir, exists
from os import remove
from gi.repository.GLib import markup_escape_text

from common.config import ConfigLoader

class Functions(object):
    ref = None
    ref2 = None

    def __new__(cls, *args, **kws):
        # Singleton
        if cls.ref is None:
            cls.ref = object.__new__(cls)
        return cls.ref

    def __init__(self):
        if Functions.ref2 is None:
            Functions.ref2 = 42

            self.userconf = ConfigLoader()

            # Just set the data and the locale dir
            if isdir('../data') and isfile('../locale/bluemindo.pot'):
                self.datadir = '../data'
                self.localedir = '../locale'
            else:
                self.datadir = '/usr/share/bluemindo'
                self.localedir = '/usr/share/locale'

    def get_hash(self, str1, str2):
        """Just return the hash for given strings"""
        md5 = md5_new()
        md5.update(str1.encode('utf-8'))
        md5.update(str2.encode('utf-8'))
        
        return str(md5.hexdigest())

    def view_encode(self, string, limit=25):
        if (len(string)) > limit:
            string = string[:limit] + '…'

        string = markup_escape_text(string)
        return string

    def unescape(string):
        """Unescape an escaped string with markup_escape_text."""
        _str = xml_unescape(string, {'&apos;': "'", '&quot;': '"'})

        return _str

    def human_length(self, length):
        """Return the length in a human-readable way"""
        lg0 = int(length / 60)
        lg1 = int(length % 60)

        if lg0 >= 0 and lg0 < 10:
            lg0 = '0' + str(lg0)

        if lg1 >= 0 and lg1 < 10:
            lg1 = '0' + str(lg1)

        lg = str(lg0) + ':' + str(lg1)
        return lg

    def clear_html(self, text, only_bold=False):
        """Return the text without html"""
        if text.startswith('<b>') and text.endswith('</b>'):
            text = text[3:-4]

        if not only_bold:
            if text.startswith('<span size="small">'):
                text = text[19:-7]

        return text

    def open_bluemindo(self, window):
        """Handle the Bluemindo's window open and change width,
        height and position on the screen."""
        width = int(self.userconf.config['Window']['width'])
        height = int(self.userconf.config['Window']['height'])
        window.resize(width, height)

        x = int(self.userconf.config['Window']['x'])
        y = int(self.userconf.config['Window']['y'])
        window.move(x, y)

    def close_bluemindo(self, window, quit=True):
        """This function is called when the Bluemindo's main window is
        closed."""
        # Backup window width, height and position
        if window is not None and window.get_properties('visible')[0]:
            width = window.get_size()[0]
            height = window.get_size()[1]
            x = window.get_position()[0]
            y = window.get_position()[1]

            self.userconf.update_key('Window', 'width', str(width))
            self.userconf.update_key('Window', 'height', str(height))
            self.userconf.update_key('Window', 'x', str(x))
            self.userconf.update_key('Window', 'y', str(y))

        # Delete the socket file and quit GTK
        if quit:
            SOCKET_NAME = '/tmp/bluemindo'
            if exists(SOCKET_NAME):
                remove(SOCKET_NAME)

            pid_filename = join(self.datadir, 'pid')
            if isfile(pid_filename):
                remove(pid_filename)

            current_playing = join(self.datadir, 'current-playing')
            if isfile(current_playing):
                remove(current_playing)

            print ('The dolphin has plunge!')
            idle_add(gtk_main_quit)
        # Hide window
        else:
            if window.get_properties('visible')[0]:
                window.hide()