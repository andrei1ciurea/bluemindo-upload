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
from gi.repository.Gtk import (ListStore, EntryCompletion, CellRendererPixbuf,
                               CellRendererText, Builder as gtk_builder)
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GLib import Error as GLIBError
from threading import Thread
from os.path import join, isfile, exists

from common.functions import Functions
from common.config import ConfigLoader
from common.webservices import LastFm

from models.song import Song
from models.album import Album

class Search:
    def __init__(self, widgets, aview):
        self.widgets = widgets

        self.aview = aview
        self.albumview = aview.albumview
        self.albumfilter = aview.albumfilter
        self.matched = aview.matched

        self.functions = Functions()
        self.userconf = ConfigLoader()

        # Create the autocompletion columns
        self.completion_model = ListStore(Pixbuf, str, str, str, str, str,
                                          str, str)
        ecomplet = EntryCompletion()
        ecomplet.set_model(self.completion_model)

        pixbufcell = CellRendererPixbuf()
        ecomplet.pack_start(pixbufcell, False)
        ecomplet.add_attribute(pixbufcell, 'pixbuf', 0)

        markupcell = CellRendererText()
        markupcell.props.xpad = 10
        ecomplet.pack_start(markupcell, True)
        ecomplet.add_attribute(markupcell, 'markup', 1)

        markupcell = CellRendererText()
        markupcell.props.xpad = 5
        ecomplet.pack_start(markupcell, False)
        ecomplet.add_attribute(markupcell, 'markup', 2)

        pixbufcell = CellRendererPixbuf()
        ecomplet.pack_start(pixbufcell, False)
        ecomplet.add_attribute(pixbufcell, 'icon_name', 3)

        ecomplet.props.text_column = 4

        def matched(widget, model, iter):
            item = model[iter]
            data_a = item[4]
            data_b = item[5]

            self.aview.matched = [data_a, data_b]
            self.albumfilter.refilter()

            if data_b == 'blm.!ARTIST!':
                # Matched an artist: show albums
                return False
            elif exists(data_b):
                # Matched a song: queue to playlist
                sng = Song(filename=item[5])
                self.aview.queue(sng)

                # Go back to empty search
                self.aview.matched = False
                searchentry = widget.get_entry()
                searchentry.set_text('')
                return True
            #elif len(self.albumfilter) == 1:
            else:
                # Matched an album: load it in a panel
                album = Album(data_b, data_a, self.songs_tree)
                if hasattr(album, 'name'):
                    self.aview.on_album_matched(album)

                    # Go back to empty search
                    self.aview.matched = False
                    searchentry = widget.get_entry()
                    searchentry.set_text('')
                    return True

        ecomplet.connect('match-selected', matched)

        searchentry = self.widgets[1].get_object('searchentry')
        searchentry.set_completion(ecomplet)
        searchentry.grab_focus()

        def do_filter(widget):
            self.albumfilter.refilter() 
            self.aview.matched = False

        searchentry.connect('changed', do_filter)
        self.searchentry = searchentry


    def generate_autocompletion(self, artists, albums, songs_tree):
        self.songs_tree = songs_tree

        albums_without_cover = []
        artists_without_picture = []

        # Launch autocompletion now that the songs tree is generated
        def append_autocompletion(name, kind):
            fnf = join(self.functions.datadir, 'image', 'logo_head_big.png')

            if kind == 1:
                # Artist
                icon = 'face-smile-symbolic'

                pic = join(self.userconf.datadir, 'modules', 'explorer',
                           'artists', self.functions.get_hash(name, 'picture'))

                try:
                    if isfile(pic):
                        pxbf = Pixbuf.new_from_file_at_scale(pic, 70, 70, True)
                    else:
                        pxbf = Pixbuf.new_from_file_at_scale(fnf, 70, 70, True)
                        artists_without_picture.append(name)
                except GLIBError:
                    pxbf = Pixbuf.new_from_file_at_scale(fnf, 70, 70, True)

                dname = '<b>' + self.functions.view_encode(name, 99) + '</b>'

                infos = ('<b>' + _('Artist') + '</b>\n' +
                         _('%s albums in collection.' % ('<b>' +
                         str(len(self.songs_tree[name])) + '</b>')))

                add = 'blm.!ARTIST!'
                add_a = ''
                add_b = ''
            elif kind == 2:
                # Album
                icon = 'media-optical-symbolic'

                artist = name[0]
                name = name[1]

                cover = join(self.userconf.datadir, 'modules', 'player',
                             'covers', self.functions.get_hash(name, artist))
                if isfile(cover):
                    pxbf = Pixbuf.new_from_file_at_scale(cover, 70, 70, True)
                else:
                    pxbf = Pixbuf.new_from_file_at_scale(fnf, 70, 70, True)
                    albums_without_cover.append([artist, name])

                dname = ('<b>' + self.functions.view_encode(name, 99) +
                         '</b>\n<i>' + self.functions.view_encode(artist, 99) +
                         '</i>')

                length = 0
                songs = 0
                for song in self.songs_tree[artist][name]:
                    songs += 1
                    length += song[7]

                hlgth = self.functions.human_length(length)
                infos = (_('%s songs' % ('<b>' + str(songs) + '</b>')) + '\n' +
                         _('Total playing time: %s.' % ('<i>' + hlgth + '</i>')
                        ))

                self.cur_pxbf = pxbf

                add = artist
                add_a = ''
                add_b = ''
            elif kind == 3:
                # Song
                icon = 'media-record-symbolic'

                artist = name[1]
                album = name[2]

                add = name[8]
                add_a = artist
                add_b = album

                name = name[0]

                dname = ('<b>' + self.functions.view_encode(name, 99) +
                         '</b>\n<i>' + self.functions.view_encode(artist, 99) +
                         ' - ' + self.functions.view_encode(album, 99) +
                         '</i>')

                infos = '<b>' + _('Song') + '</b>'

                pxbf = self.cur_pxbf

            self.completion_model.append([pxbf, dname, infos, icon, name, add,
                                          add_a, add_b])

        self.completion_model.clear()

        for a in artists:
            append_autocompletion(a, 1)

        for a in albums:
            append_autocompletion(a, 2)

            for sng in self.songs_tree[a[0]][a[1]]:
                append_autocompletion(sng, 3)

        # Retrieve album covers
        lastfm = LastFm()
        thread = Thread(group=None, target=lastfm.get_albums_pictures,
                        name='coverart',
                        kwargs={'albums': albums_without_cover})
        thread.start()

        # Retrieve artist pictures
        thread = Thread(group=None, target=lastfm.get_artists_pictures,
                        name='coverart',
                        kwargs={'artists': artists_without_picture})
        thread.start()