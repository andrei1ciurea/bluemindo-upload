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
from gi.repository.Gtk import (ListStore, FileChooserDialog, ResponseType,
                               Builder as gtk_builder, Box, Label, Button,
                               ReliefStyle, Popover)
from gi.repository.Gdk import Display
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.GObject import timeout_add
from os.path import join, isfile
from shutil import copyfile
from hashlib import md5

from common.functions import Functions
from common.config import ConfigLoader
from common.webservices import LastFm

from models.album import Album

class AlbumsView:
    def __init__(self, widgets, extensions):
        self.widgets = widgets
        self.extensions = extensions

        self.functions = Functions()
        self.userconf = ConfigLoader()
        self.dblclick = None

        # Create the IconView
        self.albumview = self.widgets[1].get_object('albumview')
        self.albummodel = ListStore(Pixbuf, str, str, str, int, str, str)

        self.albumview.set_pixbuf_column(0)
        self.albumview.set_markup_column(1)

        self.albumview.set_column_spacing(0)
        self.albumview.set_spacing(0)
        self.albumview.set_item_width(100)
        self.albumview.set_property('activate-on-single-click', False)

        # Add a filter to the ListStore model
        self.albumfilter = self.albummodel.filter_new(None)
        self.remove_filter_data()
        self.matched = False

        def filter_visible(model, iter, data):
            usrf = self.widgets[1].get_object('searchentry').get_text()
            search_a = model.get_value(iter, 3)
            search_b = model.get_value(iter, 2)
            pre_result = False

            if self.matched:
                usrf_a = self.matched[0]
                usrf_b = self.matched[1]

                if usrf_b == 'blm.!ARTIST!':
                    if usrf_a.lower() == search_b.lower():
                        # Matched an artist
                        pre_result = True
                else:   
                    if (usrf_a.lower() == search_a.lower() and
                        usrf_b.lower() == search_b.lower()):
                        # Matched an album
                        pre_result = True
            else:
                if len(model) > 0:
                    if (usrf.lower() in search_a.lower() or
                        usrf.lower() in search_b.lower()):
                        # Found an element (artist or album name is close)
                        pre_result = True
                    else:
                        # No element founded at all, return False anyway
                        return False

            # Apply filters
            fdg = self.filter_data['genre']
            fdy = self.filter_data['year']

            # Filter results by genres
            if fdg is not None and fdg != model.get_value(iter, 5):
                pre_result = False

            # Filter results by years
            if fdy is not None and fdy != model.get_value(iter, 6):
                pre_result = False

            # Return the final result
            return pre_result


        self.albumfilter.set_visible_func(filter_visible)
        self.albumview.set_model(self.albumfilter)

        # Connect to signals
        def grab_entry_focus(widget, event):
            key = event.string
            if (key.lower() in 'a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,'
                               'x,y,z,0,1,2,3,4,5,6,7,8,9'.split(',')):
                self.widgets[1].get_object('searchentry').grab_focus()
                self.widgets[1].get_object('searchentry').set_text(key)
                self.widgets[1].get_object('searchentry').set_position(-1)

        self.albumview.connect('key-press-event', grab_entry_focus)
        self.albumview.connect('selection_changed', self.on_selection_changed)


    def populate_albums(self, albums_tree, albums, songs_tree, search):
        self.albums_tree = albums_tree
        self.albums = albums
        self.songs_tree = songs_tree
        self.search_entry = search.searchentry

        # Clear the tree model first
        self.albummodel.clear()

        # Show albums in the main explorer view
        self.album_nf = []
        album_id = 0
        for alb in self.albums_tree:
            bdir = join(self.userconf.datadir, 'modules', 'player', 'covers')
            album = alb['album']
            artist = alb['artist']

            cover = join(bdir, self.functions.get_hash(album, artist))
            if isfile(cover):
                cover_px = Pixbuf.new_from_file_at_scale(cover, 150, 150, True)
            else:
                cover_px = Pixbuf.new_from_file(join(self.functions.datadir,
                                                'image', 'logo_head_big.png'))

            self.albums[album_id] = Album(artist, album, self.songs_tree)

            ap = self.albummodel.append([cover_px, '<b>' +
                                        self.functions.view_encode(album) +
                                        '</b>\n<span foreground="grey">' +
                                        self.functions.view_encode(artist) +
                                        '</span>',
                                        artist, album, album_id, '', ''])
            album_id += 1

            if not isfile(cover):
                self.album_nf.append([cover, ap, None])

        # Check if we have to regenerate thumbnail (cover not found at startup)
        if len(self.album_nf) > 0:
            def regenerate_thumb():
                new_album = []

                for alb in self.album_nf:
                    if isfile(alb[0]):
                        item_iter = alb[1]

                        cover_md5 = md5(open(alb[0], 'rb').read()).hexdigest()

                        if alb[2] == None or alb[2] != cover_md5:
                            cover_px = Pixbuf.new_from_file_at_scale(alb[0],
                                                                     150, 150,
                                                                     True)
                            self.albummodel.set_value(item_iter, 0, cover_px)
                            alb[2] = cover_md5
                            new_album.append(alb)
                    else:
                        new_album.append(alb)

                if len(new_album) > 0:
                    self.album_nf = new_album
                    return True

            timeout_add(15000, regenerate_thumb)


    def on_album_matched(self, album):
        for item in self.albummodel:
            if item[2] == album.artist and item[3] == album.name:
                self.on_selection_changed(self.albumview, album)


    def on_selection_changed(self, icon_view, album=None):
        popup = Popover.new(self.albumview)
        popup.set_size_request(810, 240)

        if album is None:
            selection = icon_view.get_selected_items()
            if len(selection) != 1:
                return

            path = selection[0]
            treeiter = self.albumfilter.get_iter(path)

            isset, path, cell = icon_view.get_cursor()
            isset, rect = icon_view.get_cell_rect(path, cell)
            popup.set_pointing_to(rect)

            album_id = self.albumfilter.get_value(treeiter, 4)
            album_obj = self.albums[album_id]
        else:
            album_obj = album
            popup.set_relative_to(self.search_entry)

        # Handle double clicks
        def empty_dblclick():
            self.dblclick = None

        if self.dblclick is None:
            self.dblclick = album_obj
            timeout_add(1000, empty_dblclick)
        elif self.dblclick == album_obj:
            self.play(album_obj)
            return

        album = album_obj.name
        artist = album_obj.artist

        glade_album = join(self.functions.datadir, 'glade', 'albumview.ui')
        box = gtk_builder()
        box.set_translation_domain('bluemindo')
        box.add_from_file(glade_album)
        popup.add(box.get_object('box1'))

        box.get_object('label_album').set_text(album)
        box.get_object('label_artist').set_text(artist)

        bdir = join(self.userconf.datadir, 'modules', 'player', 'covers')
        cover = join(bdir, self.functions.get_hash(album, artist))
        if isfile(cover):
            cover_px = Pixbuf.new_from_file_at_scale(cover, 180, 180, True)
        else:
            cover_px = Pixbuf.new_from_file(join(self.functions.datadir,
                                            'image', 'logo_head_big.png'))

        box.get_object('album_cover').set_from_pixbuf(cover_px)

        def play_album(wdg, album):
            self.play(album)

        def queue_album(wdg, album):
            self.queue(album)

        def change_cover(wdg, ka, album):
            artist_name = album.artist
            album_name = album.name

            fcdialog = FileChooserDialog(
                        title=_('Change the cover picture for this album'),
                        buttons=(_('Select'), ResponseType.OK))

            fcdialog.set_transient_for(self.widgets[0][11])
            response = fcdialog.run()
            if response == ResponseType.OK:
                filename = fcdialog.get_filename()

                datadir = self.userconf.datadir
                hash_a = self.functions.get_hash(album_name, artist_name)
                pictures_dir = join(datadir, 'modules', 'player', 'covers')
                album_file = join(pictures_dir, hash_a)

                copyfile(filename, album_file)

                new = Pixbuf.new_from_file_at_scale(album_file, 180, 180, True)
                box.get_object('album_cover').set_from_pixbuf(new)

            fcdialog.destroy()

        box.get_object('button_play').connect('clicked', play_album, album_obj)

        box.get_object('button_add').connect('clicked', queue_album, album_obj)

        box.get_object('coverevent').connect('button-press-event',
                                             change_cover, album_obj)

        i = 0
        a = -1
        previous_column = 0

        grid_songs = box.get_object('grid_songs')
        grid_songs.set_size_request(-1, 200)
        grid_songs.set_column_spacing(5)

        try:
            kids = grid_songs.get_children()
            for kid in kids:
                grid_songs.remove(kid)
        except IndexError:
            pass

        for song in album_obj.tracks:
            i += 1
            a += 1

            def queue(wdg, song):
                self.queue(song)

            def play(wdg, song):
                self.play(song)

            song_wdg = Box(spacing=0)
            song_btr = Button()
            song_btr.connect('clicked', play, song)
            song_btr.set_relief(ReliefStyle.NONE)
            song_btr_content = Box(spacing=0)
            song_btr.add(song_btr_content)

            song_tr = Label()
            song_tr.set_markup('<span foreground="grey">' + str(song.track)
                               + '</span>')
            song_tr.set_width_chars(3)
            song_btr_content.pack_start(song_tr, False, True, 0)
            song_ti = Label()
            song_ti.set_markup('<b>' + self.functions.view_encode(song.title, 22)
                               + '</b>')
            song_ti.set_alignment(0.0, 0.5)
            song_ti.set_size_request(190, -1)
            song_btr_content.pack_start(song_ti, False, False, 0)

            length = self.functions.human_length(song.length)
            song_le = Label()
            song_le.set_markup('<span foreground="grey">' + length
                               + '</span>')
            song_le.set_width_chars(5)
            song_btr_content.pack_start(song_le, False, True, 0)

            song_wdg.pack_start(song_btr, False, False, 0)

            song_add = Button.new_from_icon_name('list-add-symbolic', 0)
            song_add.set_property('relief', 2)
            song_add.set_size_request(14, 14)
            song_add.connect('clicked', queue, song)
            song_wdg.pack_start(song_add, False, False, 0)

            if i <= len(album_obj.tracks)/2:
                column = 0
                previous_column = 0
                row = a
            else:
                if previous_column == 0:
                    a = 0
                column = 1
                previous_column = 1
                row = a

            grid_songs.attach(song_wdg, column, row, 1, 1)
        popup.show_all()


    def play(self, usrobject):
        kind = usrobject.kind

        if kind == 'album':
            self.extensions.load_event('OnPlayNewAlbum', usrobject)
        else:
            self.extensions.load_event('OnPlayNewSong', usrobject)

    def queue(self, usrobject):
        kind = usrobject.kind

        if kind == 'album':
            self.extensions.load_event('OnAlbumQueued', usrobject)
        else:
            self.extensions.load_event('OnSongQueued', usrobject)

    def generate_filter_data(self, album_data):
        for element in self.albummodel:
            artist = element[2]
            album = element[3]

            datalb = album_data[artist][album]
            datalb_genre = datalb['genre']
            datalb_year = datalb['year']

            element[5] = datalb_genre
            element[6] = datalb_year

    def add_filter_data(self, value, field):
        self.filter_data[field] = value
        self.albumfilter.refilter()

    def remove_filter_data(self, cmb=None):
        if cmb is None:
            self.filter_data = {'genre': None, 'year': None}
        else:
            self.filter_data[cmb] = None
        self.albumfilter.refilter()