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

from gettext import gettext as _
from gi.repository.Gtk import (FileChooserDialog, FileChooserAction,
                               ResponseType, Builder as gtk_builder)
from gi.repository.Gdk import threads_enter, threads_leave
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GObject import markup_escape_text, idle_add
from threading import Thread
from os.path import join
from random import randrange
from sys import exit

from modules.explorer.musicdb import MusicDatabase
from modules.explorer.albumsview import AlbumsView
from modules.explorer.search import Search
from modules.explorer.filter import Filter

from common.functions import Functions
from common.config import ConfigLoader

from models.album import Album
from models.song import Song

class Explorer:
    def __init__(self, extensionsloader):
        self.extensions = extensionsloader
        self.module = {'name': 'Explorer'}

        self.functions = Functions()
        self.userconf = ConfigLoader()

        self.songs_tree = {}
        self.albums = {}

        # Create the Albums view
        def launch_explorer(wdg):
            self.widgets = wdg

            self.aview = AlbumsView(self.widgets, self.extensions)
            self.search = Search(self.widgets, self.aview)
            self.filter = Filter(self.widgets, self.aview)

            # Populate the view
            self.populate()

            # Connect to signals
            def repopulate(wdg):
                self.extensions.load_event('OnAbortPlayback')
                self.populate(True)

            self.widgets[0][3].connect('clicked', repopulate)


        self.extensions.connect('OnBluemindoStarted', launch_explorer)
        self.extensions.connect('AskShuffleSong', self.shuffle_song_asked)

    def populate(self, force_scan=False):
        threads_enter()

        # Do we have a working directory or not?
        if self.userconf.config['Explorer']['folder'] == '':
            fcdialog = FileChooserDialog(
                        title=_('Open your music directory'),
                        action=FileChooserAction.SELECT_FOLDER,
                        buttons=(_('Select'), ResponseType.OK))

            fcdialog.set_transient_for(self.widgets[0][11])
            response = fcdialog.run()
            if response == ResponseType.OK:
                foldername = fcdialog.get_filename()
                self.userconf.update_key('Explorer', 'folder', foldername)
                force_scan = True
            else:
                print("Bluemindo can't work without opening a music " +
                      "directory. Exiting…")
                exit(0)

            fcdialog.destroy()

        # Call database
        musicdb = MusicDatabase(self.userconf.config['Explorer']['folder'])

        # Do we scan for new files?
        if (bool(int(self.userconf.config['Explorer']['scan_at_startup'])) or
            force_scan):
            def do_scan():
                # Freeze user interface
                gldfile = join(self.functions.datadir, 'glade', 'loading.ui')
                win = gtk_builder()
                win.set_translation_domain('bluemindo')
                win.add_from_file(gldfile)
                box_content = win.get_object('box1')

                # Create an interface to help the user waiting for the job
                bluemindo = join(self.functions.datadir, 'image', 'bluemindo.png')
                img = win.get_object('image')
                cover_px = Pixbuf.new_from_file(bluemindo)
                idle_add(img.set_from_pixbuf, cover_px)

                idle_add(win.get_object('label').set_markup,
                         '<span size="x-large"><b>' +
                         _('Reloading music database.') + '</b></span>')

                idle_add(self.widgets[0][2].set_sensitive, False)
                idle_add(self.widgets[0][3].set_sensitive, False)
                idle_add(self.widgets[0][5].set_sensitive, False)
                idle_add(self.widgets[0][6].set_sensitive, False)
                idle_add(self.widgets[0][7].set_sensitive, False)
                idle_add(self.widgets[0][8].set_sensitive, False)

                idle_add(self.widgets[1].get_object('box1').add, box_content)

                lbl = win.get_object('label_info')
                idle_add(lbl.set_text,
                         _('Starting… Prepares to search for new files.'))

                # Update GUI
                box_content.show_all()
                self.widgets[1].get_object('box2').hide()

                # Do the scanning
                pb = win.get_object('progressbar')
                musicdb.scan(lbl, pb)

                # Show original GUI
                idle_add(self.widgets[0][2].set_sensitive, True)
                idle_add(self.widgets[0][3].set_sensitive, True)
                idle_add(box_content.hide)
                idle_add(self.widgets[1].get_object('box2').show_all)
                idle_add(self.create_view)

            thread = Thread(group=None, target=do_scan,
                            name='scanning', args=())
            thread.start()
        else:
            self.create_view()

        threads_leave()

    def create_view(self):
        # Call database
        musicdb = MusicDatabase(self.userconf.config['Explorer']['folder'])
        self.database = musicdb.load()

        self.albums_tree = []
        album_names = []
        album_iter = {}

        # Activate player buttons
        self.widgets[0][5].set_sensitive(True)
        self.widgets[0][6].set_sensitive(True)
        self.widgets[0][7].set_sensitive(True)
        self.widgets[0][8].set_sensitive(True)

        # Create the tree artists→albums→songs
        def unique(seq, keepstr=True):
            """This function ensures there are only unique values."""
            t = type(seq)
            if t in (str, str):
                t = (list, ''.join)[bool(keepstr)]
            seen = []
            return t(c for c in seq if not (c in seen or seen.append(c)))

        # Create the songs tree
        songs_tree = {}
        artists = []
        albums = []
        albums_dl = []

        for result in self.database:
            artists.append(result[1])
            albums.append((result[1], result[2]))

        artists = unique(artists)
        albums = unique(albums)

        for a in artists:
            songs_tree[a] = {}

        for a in albums:
            songs_tree[a[0]][a[1]] = []

        # Add songs
        for result in self.database:
            songs_tree[result[1]][result[2]].append(result)

        # Sort songs
        for artist in songs_tree.values():
            for album in artist.values():
                album.sort(key=lambda student: student[3])

        self.songs_tree = songs_tree

        i = 0
        for art in self.songs_tree:
            for alb in self.songs_tree[art]:
                album_names.append(alb)
                self.albums_tree.append({'album': alb, 'artist': art})
                i = i + 1

        # Sort everything
        self.albums_tree.sort(key=lambda item: item['album'].lower())
        self.albums_tree.sort(key=lambda item: item['artist'].lower())

        # Send the music tree to all extensions
        self.extensions.load_event('OnSongsTreeCreated', self.songs_tree)

        # Launch explorer GUI
        self.search.generate_autocompletion(artists, albums, self.songs_tree)
        self.aview.populate_albums(self.albums_tree, self.albums, self.songs_tree, self.search)
        self.filter.launch(self.albums_tree, self.songs_tree, self.aview)


    def shuffle_song_asked(self):
        if len(self.database) > 1:
            index = randrange(len(self.database))
            song_inf = self.database[index]

            song = Song(filename=song_inf[8])
            self.extensions.load_event('OnPlayNewSong', song)
