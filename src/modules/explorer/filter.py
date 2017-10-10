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
from gi.repository.Gtk import (Builder as gtk_builder, ListStore,
                               CellRendererText)
from os.path import join

from common.functions import Functions
from common.config import ConfigLoader

from models.album import Album

class Filter:
    def __init__(self, widgets, aview):
        self.widgets = widgets

        self.functions = Functions()
        self.userconf = ConfigLoader()

        # GUI
        self.filter_button = self.widgets[1].get_object('tool-filter')
        self.filter_button.connect('clicked', self.on_button_clicked)

        gladefile = join(self.functions.datadir, 'glade', 'filterbar.ui')
        self.fbox = gtk_builder()
        self.fbox.set_translation_domain('bluemindo')
        self.fbox.add_from_file(gladefile)
        self.filter_box = self.fbox.get_object('infobar')

        wdg_place = self.widgets[1].get_object('filter-emplacement')
        wdg_place.add(self.filter_box)

        self.fbox.get_object('label_filter').set_text(_('Filter the results:'))

        # Create ComboBoxes
        self.genre_fstore = ListStore(int, str)
        self.genre_fcombo = self.fbox.get_object('combobox-genre')
        self.genre_fcombo.set_model(self.genre_fstore)
        renderer_text = CellRendererText()
        self.genre_fcombo.pack_start(renderer_text, True)
        self.genre_fcombo.set_entry_text_column(1)
        self.genre_fcombo.add_attribute(renderer_text, 'text', 1)

        self.year_fstore = ListStore(int, str)
        self.year_fcombo = self.fbox.get_object('combobox-year')
        self.year_fcombo.set_model(self.year_fstore)
        renderer_text = CellRendererText()
        self.year_fcombo.pack_start(renderer_text, True)
        self.year_fcombo.set_entry_text_column(1)
        self.year_fcombo.add_attribute(renderer_text, 'text', 1)


    def on_button_clicked(self, widget):
        if self.filter_box.props.visible is True:
            self.filter_box.hide()
        else:
            self.filter_box.show_all()

        # Reset filters
        self.genre_fcombo.set_active(0)
        self.year_fcombo.set_active(0)

    def launch(self, albums_tree, songs_tree, aview):
        self.albums_tree = albums_tree
        self.songs_tree = songs_tree
        self.aview = aview

        album_data = {}
        data_genre = []
        data_year = []

        # Gather data
        for item in self.albums_tree:
            item_artist = item['artist']
            item_album = item['album']

            if item_artist not in album_data.keys():
                album_data[item_artist] = {}

            album_data[item_artist][item_album] = {}

            album = Album(item_artist, item_album, self.songs_tree)

            album_genre = ''
            album_year = ''

            for sng in album.tracks:
                if album_genre == '':
                    album_genre = sng.genre

                if album_year == '':
                    album_year = sng.year

            if album_genre != '' and album_genre not in data_genre:
                data_genre.append(album_genre)

            if album_year != '' and album_year not in data_year:
                data_year.append(album_year)

            album_data[item_artist][item_album]['genre'] = album_genre
            album_data[item_artist][item_album]['year'] = album_year

        # Populate combobox
        self.genre_fstore.clear()
        self.genre_fstore.append([-2, _('All genres')])
        self.genre_fstore.append([-1, ''])

        data_genre.sort()
        i = 0
        for genre in data_genre:
            self.genre_fstore.append([i, genre])
            i += 1

        self.year_fstore.clear()
        self.year_fstore.append([-2, _('All years')])
        self.year_fstore.append([-1, ''])

        data_year.sort()
        i = 0
        for year in data_year:
            self.year_fstore.append([i, year])
            i += 1

        def combo_sep(model, iter):
            if model[iter][0] == -1:
                return True
        self.year_fcombo.set_row_separator_func(combo_sep)
        self.genre_fcombo.set_row_separator_func(combo_sep)

        self.aview.generate_filter_data(album_data)

        self.genre_fcombo.connect('changed', self.on_fcombo_changed, 'genre')
        self.year_fcombo.connect('changed', self.on_fcombo_changed, 'year')

        # Hide filters
        self.filter_box.hide()
        self.filter_button.set_active(False)

    def on_fcombo_changed(self, widget, cmb):
        path = widget.get_active()

        try:
            if cmb == 'genre':
                item_value = self.genre_fstore[path][1]
                item_key = self.genre_fstore[path][0]
            else:
                item_value = self.year_fstore[path][1]
                item_key = self.year_fstore[path][0]
        except IndexError:
            item_key = -42

        if item_key >= 0:
            self.aview.add_filter_data(item_value, cmb)
        else:
            self.aview.remove_filter_data(cmb)