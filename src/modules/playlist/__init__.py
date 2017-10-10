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

from os.path import join
from time import sleep
from gi.repository.Gtk import (ListStore, CellRendererPixbuf, CellRendererText,
                               TreeViewColumn, Builder as gtk_builder, Popover,
                               TreePath)
from threading import Thread
from gi.repository.Gdk import (threads_enter, threads_leave, KEY_Return,
                               KEY_Delete)
from gi.repository.Pango import EllipsizeMode
from gettext import gettext as _
from random import randrange

from common.sqlite import SQLite
from common.functions import Functions
from common.config import ConfigLoader
from common.webservices import LastFm
from modules.explorer.musicdb import MusicDatabase
from modules.playlist.playlists import Playlists

from models.song import Song
from models.album import Album

class Playlist:
    def __init__(self, extensionsloader):
        self.extensions = extensionsloader
        self.module = {'name': 'Playlist'}

        self.functions = Functions()
        self.userconf = ConfigLoader()

        self.config = {}
        rpt = self.userconf.config['Playlist']['repeat']
        self.config['repeat'] = bool(int(rpt))
        shf = self.userconf.config['Playlist']['shuffle']
        self.config['shuffle'] = bool(int(shf))
        shm = self.userconf.config['Playlist']['shuffle_mode']
        self.config['shuffle_mode'] = shm

        self.lastfm = LastFm()
        self.playlists_mgmnt = Playlists()

        self.playlist_content = {}
        self.playlist_identifier = 0
        self.playlist_current = None
        self.current_playlist_id = 0
        self.user_playlists = {}
        self.last_user_playlist = None

        self.similar_artists = []
        self.is_in_similar_thread = False

        # Create the Playlist view
        def launch_playlist(wdg):
            self.widgets = wdg[1]

            self.playlist_label = self.widgets.get_object('label_playlist')
            self.playlist_repeat = self.widgets.get_object('tool-repeat')
            self.playlist_shuffle = self.widgets.get_object('tool-shuffle')
            self.playlist_clean = self.widgets.get_object('tool-clean')
            self.playlist_combo = self.widgets.get_object('combo-playlist')
            self.playlist_save = self.widgets.get_object('tool-saveplaylist')
            self.playlist_lyrics = self.widgets.get_object('tool-lyrics')

            self.playlist_tree = self.widgets.get_object('treeview_playlist')
            self.playlist_tree.set_headers_visible(False)
            self.playlist_tree.props.reorderable = True
            self.playlist_tree.connect('key_press_event', self.key_pressed)
            self.playlist_tree.connect('row_activated', self.row_activated)

            self.liststore = ListStore(str, str, str, str, int)
            self.playlist_tree.set_model(self.liststore)

            renderer_pix = CellRendererPixbuf()
            column_pixbuf = TreeViewColumn('1', renderer_pix, icon_name=0)
            column_pixbuf.set_fixed_width(18)
            self.playlist_tree.append_column(column_pixbuf)

            renderer_text = CellRendererText()
            column_text = TreeViewColumn('2', renderer_text, markup=1)
            column_text.props.expand = True
            column_text.props.max_width = 192
            self.playlist_tree.append_column(column_text)

            column_text = TreeViewColumn('3', renderer_text, markup=2)
            column_text.set_fixed_width(40)
            self.playlist_tree.append_column(column_text)

            self.repeat_btn = self.widgets.get_object('tool-repeat')
            if self.config['repeat']:
                self.repeat_btn.set_active(True)
            self.repeat_btn.connect('clicked', self.toggle, 'repeat')

            self.shuffle_btn = self.widgets.get_object('tool-shuffle')
            if self.config['shuffle']:
                self.shuffle_btn.set_active(True)
            self.shuffle_btn.connect('clicked', self.toggle, 'shuffle')

            def clean_wdg(widget):
                # Clean playlist
                self.clean()

                # Show popover
                if self.current_playlist_id > 3:
                    self.clean_btn.set_sensitive(True)
                    self.clean_pop.show_all()

            self.clean_btn = self.widgets.get_object('tool-clean')
            self.clean_btn.connect('clicked', clean_wdg)
            self.clean_pop = Popover.new(self.clean_btn)
            self.clean_pop.set_size_request(100, 30)

            gtkpla = join(self.functions.datadir, 'glade', 'plist-del-pop.ui')
            win = gtk_builder()
            win.set_translation_domain('bluemindo')
            win.add_from_file(gtkpla)
            hbox = win.get_object('box-playlist')
            lbl = win.get_object('label')
            lbl.set_text(_('Do you also want to remove the playlist?'))
            btn = win.get_object('del-btn')
            btn.set_label(_('Delete'))
            btn.connect('clicked', self.delete_playlist)
            self.clean_pop.add(hbox)

            # Populate combobox
            self.combolist = ListStore(int, str)

            self.combobox = self.widgets.get_object('combobox')
            self.combobox.set_model(self.combolist)
            self.combobox.set_popup_fixed_width(False)
            self.combobox.props.expand = False

            renderer_text = CellRendererText()
            renderer_text.props.ellipsize = EllipsizeMode.END
            self.combobox.pack_start(renderer_text, True)
            self.combobox.set_entry_text_column(1)
            self.combobox.add_attribute(renderer_text, 'text', 1)

            self.combolist.append([0, _('Current')])
            self.combolist.append([1, _('Top 50 songs')])
            self.combolist.append([2, _('Top 10 albums')])

            playlists = self.playlists_mgmnt.get_playlists()

            if len(playlists) > 0:
                self.combolist.append([3, ''])
                item_id = 3

                playlists.sort(key=lambda it: it[1])
                for item in playlists:
                    item_id += 1
                    self.combolist.append([item_id, item])
                    self.user_playlists[item_id] = item
                    self.last_user_playlist = item_id

            def combo_sep(model, iter):
                if model[iter][0] == 3:
                    return True
            self.combobox.set_row_separator_func(combo_sep)

            def on_combo_changed(widget):
                path = widget.get_active()
                item_id = self.combolist[path][0]

                # First, clean the playlist
                self.clean(None)

                # Second, populate the playlist
                if item_id > 0:
                    self.populate(item_id)

                # Then, update playlist identifier
                self.current_playlist_id = item_id

                # Show delete/remove button if the playlist is from the user
                if item_id > 3:
                    self.clean_btn.set_sensitive(True)

            self.combobox.set_active(0)
            self.combobox.connect('changed', on_combo_changed)
            
            self.tool_save = self.widgets.get_object('tool-saveplaylist')
            self.tool_save.connect('clicked', self.save_playlist)
            self.save_pop = Popover.new(self.tool_save)
            self.save_pop.set_size_request(100, 30)

            gtkpla = join(self.functions.datadir, 'glade', 'plist-add-pop.ui')
            win = gtk_builder()
            win.set_translation_domain('bluemindo')
            win.add_from_file(gtkpla)
            hbox = win.get_object('box-playlist')
            self.save_pop.add(hbox)

            self.save_entry = win.get_object('save-entry')
            self.save_entry.connect('key_press_event', self.save_playlist_key)
            self.save_btn = win.get_object('save-btn')
            self.save_btn.connect('clicked', self.save_playlist_button)
            self.save_btn.set_label(_('Save'))

            self.clean_btn.set_sensitive(False)
            self.tool_save.set_sensitive(False)

        # Acquire the songs tree
        def acquire_tree(st):
            self.songs_tree = st

        self.extensions.connect('OnBluemindoStarted', launch_playlist)
        self.extensions.connect('OnSongsTreeCreated', acquire_tree)
        self.extensions.connect('OnSongQueued', self.on_new_song_queued)
        self.extensions.connect('OnAlbumQueued', self.on_new_album_queued)
        self.extensions.connect('AskPreviousSong', self.ask_previous_song)
        self.extensions.connect('AskNextSong', self.ask_next_song)
        self.extensions.connect('HasStartedSong', self.song_started)


    def toggle(self, widget, action):
        if action == 'repeat' and self.config['repeat']:
            self.config['repeat'] = False
            self.repeat_btn.set_active(False)
            self.userconf.update_key('Playlist', 'repeat', str(int(False)))
        elif action == 'repeat' and not self.config['repeat']:
            self.config['repeat'] = True
            self.repeat_btn.set_active(True)
            self.userconf.update_key('Playlist', 'repeat', str(int(True)))
        elif action == 'shuffle' and self.config['shuffle']:
            self.config['shuffle'] = False
            self.shuffle_btn.set_active(False)
            self.userconf.update_key('Playlist', 'shuffle', str(int(False)))
        elif action == 'shuffle' and not self.config['shuffle']:
            self.config['shuffle'] = True
            self.shuffle_btn.set_active(True)
            self.userconf.update_key('Playlist', 'shuffle', str(int(True)))

    def row_activated(self, widget, path, column):
        item_iter = self.liststore.get_iter(path)

        # Get the founded element.
        item_identifier = self.liststore.get_value(item_iter, 4)
        current_item = self.playlist_content[item_identifier]

        # The element is a song.
        if self.playlist_content[item_identifier].kind == 'song':
            self.playlist_current = [item_iter, item_identifier, None]
            self.extensions.load_event('OnPlayNewSong', current_item)
        # The element is an album.
        else:
            self.extensions.load_event('OnAbortPlayback')
            sng = self.playlist_content[item_identifier].tracks[0]
            self.playlist_current = [item_iter, item_identifier, 0]
            self.extensions.load_event('OnPlayNewSong', sng)

    def key_pressed(self, widget, eventkey):
        if eventkey.get_keyval()[1] == KEY_Delete:
            # Delete an item from the playlist
            selection = self.playlist_tree.get_selection()
            selected = selection.get_selected_rows()
            liststore = selected[0]
            listpath = selected[1]

            if len(listpath) > 0:
                selpath = listpath[0]
                playlist_identifier = liststore[selpath][4]

                # Are we removing the currently playing item?
                if self.playlist_current is not None:
                    item_iter, item_path, item_in_album = self.playlist_current
                    if selpath == TreePath.new_from_string(str(item_path)):
                        self.playlist_current = None

                # Removal
                del self.playlist_content[playlist_identifier]
                del liststore[selpath]

    def clean(self, data=None):
        self.playlist_content = {}
        self.playlist_identifier = 0
        self.playlist_current = None
        self.liststore.clear()

        # Update GUI
        self.clean_btn.set_sensitive(False)
        self.tool_save.set_sensitive(False)

    def populate(self, playlist_id):
        if playlist_id in (1, 2):
            # Automatic playlists based on listening stats
            if playlist_id == 1:
                tb = 'stats_songs'
                lm = 50
            elif playlist_id == 2:
                tb = 'stats_albums'
                lm = 10

            result = []
            txt = ('select * from %s order by tracks desc limit %u' % (tb, lm))

            sql = SQLite()
            cur = sql.execute(txt)
            for sg in cur:
                result.append(sg)
            sql.close()

            for item in result:
                if playlist_id == 1:
                    sng = Song(filename=item[0])
                    if hasattr(sng, 'title'):
                        self.on_new_song_queued(sng)
                elif playlist_id == 2:
                    album_name = item[0]
                    for it in self.songs_tree:
                        if album_name in self.songs_tree[it]:
                            self.on_new_album_queued(Album(it, album_name,
                                                           self.songs_tree))
                            break
        elif playlist_id > 3:
            # User-created playlists
            user_plist = self.user_playlists[playlist_id]
            plist = self.playlists_mgmnt.load_playlist(user_plist)

            for item in plist:
                sng = Song(filename=item)
                if hasattr(sng, 'title'):
                    self.on_new_song_queued(sng)

    def delete_playlist(self, widget):
        if self.current_playlist_id > 3:
            user_plist = self.user_playlists[self.current_playlist_id]
            self.playlists_mgmnt.delete_playlist(user_plist)

            # Delete the playlist from the list
            del self.user_playlists[self.current_playlist_id]

            cblid = 0
            for item in self.combolist:
                if item[0] == self.current_playlist_id:
                    del self.combolist[cblid]
                    break
                cblid += 1

            # Move back to "Current" playlist
            self.combobox.set_active(0)

    def save_playlist_key(self, widget, eventkey):
        if eventkey.get_keyval()[1] == KEY_Return:
            self.save_playlist_button(None)

    def save_playlist_button(self, widget):
        user_entry = self.save_entry.get_text()
        user_entry = user_entry.replace('\\', '-')
        user_entry = user_entry.replace('/', '-')
        user_entry = user_entry.replace('*', '-')
        user_entry = user_entry.replace('|', '-')

        if len(user_entry) > 0:
            rtn_value = self.playlists_mgmnt.create_new_playlist(user_entry)

            if rtn_value:
                self.save_pop.hide()

                # Add playlist to GUI
                if self.last_user_playlist is None:
                    self.combolist.append([3, ''])
                    self.last_user_playlist = 3

                self.last_user_playlist += 1
                self.combolist.append([self.last_user_playlist, user_entry])
                self.user_playlists[self.last_user_playlist] = user_entry

                # Write the playlist
                self.write_playlist(user_entry)

                # Select the new playlist
                self.combobox.set_active(self.last_user_playlist)

    def save_playlist(self, widget):
        if self.current_playlist_id < 3:
            # Create a new playlist
            self.save_entry.set_text('')
            self.save_pop.show_all()
        elif self.current_playlist_id > 3:
            # Update an existing playlist
            user_plist = self.user_playlists[self.current_playlist_id]
            self.write_playlist(user_plist)

    def write_playlist(self, user_plist):
        plist_content = []
        for item in self.liststore:
            item_id = item[4]
            plist_content.append(self.playlist_content[item_id])

        self.playlists_mgmnt.write_playlist(user_plist, plist_content)

    def on_new_song_queued(self, song_info):
        title = song_info.title
        artist = song_info.artist
        album = song_info.album
        filename = song_info.filename
        length = self.functions.human_length(song_info.length)

        self.liststore.append(('audio-x-generic-symbolic', '<b>' +
                               self.functions.view_encode(title, 99) +
                               '</b>\n' + self.functions.view_encode(artist),
                               '<span foreground="grey">' +
                               length + '</span>',
                               filename, self.playlist_identifier))

        self.playlist_content[self.playlist_identifier] = song_info
        self.playlist_identifier += 1

        # Update GUI
        self.clean_btn.set_sensitive(True)
        self.tool_save.set_sensitive(True)

    def on_new_album_queued(self, album_info):
        artist = album_info.artist
        album = album_info.name
        songs_count = str(len(album_info.tracks)) + ' ♫'

        self.liststore.append(('media-optical-symbolic', '<b>' +
                               self.functions.view_encode(album, 99) +
                               '</b>\n' + self.functions.view_encode(artist),
                               '<span foreground="grey">' +
                               songs_count + '</span>', '[album]',
                               self.playlist_identifier))

        self.playlist_content[self.playlist_identifier] = album_info
        self.playlist_identifier += 1

        # Update GUI
        self.clean_btn.set_sensitive(True)
        self.tool_save.set_sensitive(True)

    def ask_next_song(self, current_song):
        self.ask_for_a_song(True, current_song)

    def ask_previous_song(self, current_song):
        self.ask_for_a_song(False, current_song)

    def ask_for_a_song(self, next=True, current_song=None):
        def walk_in_playlist(item_iter, next=True):
            base_item_iter = item_iter
            if item_iter is None:
                # Find first song.
                item_iter = self.liststore.get_iter_first()
            elif next:
                # Find next song.
                path = self.liststore.get_path(self.playlist_current[0])
                path_int = int(path.to_string())
                max_id = len(self.playlist_content) - 1

                if (path_int + 1 <= max_id): # There is a song to launch!
                    item_iter = self.liststore.get_iter(path_int + 1)
                else: # There is no song to launch!
                    if not self.config['repeat']:
                        self.extensions.load_event('OnAbortPlayback')
                        return
                    else:
                        item_iter = self.liststore.get_iter_first()
            elif not next:
                # Find previous song.
                path = self.liststore.get_path(self.playlist_current[0])
                path_int = int(path.to_string())
                max_id = len(self.playlist_content) - 1

                if (path_int -1 >= 0): # There is a song to launch.
                    item_iter = self.liststore.get_iter(path_int - 1)
                else: # There is no song to launch!
                    if not self.config['repeat']:
                        self.extensions.load_event('OnAbortPlayback')
                        return
                    else:
                        item_iter = self.liststore.get_iter_from_string(str(max_id))

            # Get the founded element.
            item_identifier = self.liststore.get_value(item_iter, 4)
            current_item = self.playlist_content[item_identifier]

            def launch_founded_item(item_identifier, item_iter, current_item):
                # The element is a song.
                if self.playlist_content[item_identifier].kind == 'song':
                    self.playlist_current = [item_iter, item_identifier, None]
                    self.extensions.load_event('OnPlayNewSong', current_item)
                # The element is an album.
                else:
                    self.extensions.load_event('OnAbortPlayback')
                    sng = self.playlist_content[item_identifier].tracks[0]
                    sng.rg_mode_guess = 'album'
                    self.playlist_current = [item_iter, item_identifier, 0]
                    self.extensions.load_event('OnPlayNewSong', sng)

            # Are we currently listening from an album?
            if base_item_iter is not None:
                kind = self.playlist_content[self.playlist_current[1]].kind

                if kind == 'album':
                    base_item_identifier = self.liststore.get_value(base_item_iter, 4)
                    tracks = self.playlist_content[self.playlist_current[1]].tracks
                    max_sng = len(tracks) - 1

                    if next:
                        if self.playlist_current[2] < max_sng:
                            item_in_album = self.playlist_current[2] + 1
                        else:
                            return launch_founded_item(item_identifier, item_iter, current_item)
                    elif not next:
                        if self.playlist_current[2] - 1 > -1:
                            item_in_album = self.playlist_current[2] - 1
                        else:
                            return launch_founded_item(item_identifier, item_iter, current_item)

                    sng = self.playlist_content[base_item_identifier].tracks[item_in_album]
                    sng.rg_mode_guess = 'album'
                    self.playlist_current = [base_item_iter, base_item_identifier, item_in_album]
                    self.extensions.load_event('OnPlayNewSong', sng)
                    return

            launch_founded_item(item_identifier, item_iter, current_item)

        if len(self.playlist_content) == 0:
            # Playlist is empty.
            if not self.config['shuffle']:
                # Shuffle disabled: abort playback.
                self.extensions.load_event('OnAbortPlayback')
            else:
                # Shuffle enabled.
                if self.config['shuffle_mode'] == 'random':
                    # Random mode: seek for shuffle song.
                    self.extensions.load_event('AskShuffleSong')
                elif self.config['shuffle_mode'] == 'similar':
                    # Similar mode: seek for a similar song.
                    if len(self.similar_artists) == 0:
                        # No similar song founded: seek for any one.
                        self.extensions.load_event('AskShuffleSong')
                        return

                    # Choose one song in the list of similar artists
                    index = randrange(len(self.similar_artists))
                    artist = self.similar_artists[index]

                    mdb = MusicDatabase(None)
                    songs_list = mdb.load_from_artist(artist)
                    if len(songs_list) > 1:
                        index = randrange(len(songs_list))
                        song = songs_list[index]

                        sng = Song(filename=song[8])
                        print ('[SIMILAR] Playing a song from ' + sng.artist)
                        self.extensions.load_event('OnPlayNewSong', sng)
                    else:
                        self.extensions.load_event('AskShuffleSong')
        else:
            # Playlist is not empty, walk in it!
            if self.playlist_current is None:
                # Currently no current item in playlist, choose the first one!
                walk_in_playlist(None)
            else:
                # The current playling song is in the playlist!
                if next:
                    walk_in_playlist(self.playlist_current[0])
                else:
                    walk_in_playlist(self.playlist_current[0], False)


    def song_started(self, song):
        # First, try to download a few similar artists names
        if self.config['shuffle_mode'] == 'similar':
            def download_similars():
                threads_enter()
                art = self.lastfm.get_similar_artists(song.artist)

                self.similar_artists = []
                mdb = MusicDatabase(None)

                for artist in art:
                    if mdb.artist_exists(artist):
                        self.similar_artists.append(artist)

                self.is_in_similar_thread = False
                threads_leave()

            if not self.is_in_similar_thread:
                self.is_in_similar_thread = True
                thread = Thread(group=None, target=download_similars,
                                name='similars', args=())
                thread.start()

        # Second, update statistics for this song
        song.increment_statistics()
        alb = Album(song.artist, song.album, self.songs_tree)
        alb.increment_statistics()

        # Then, highlight currently playing song/album if it's in playlist
        if self.playlist_current is not None:
            # Currently playing item is in the playlist
            item_iter, item_path, item_in_album = self.playlist_current

            # Remove marker of all items
            for item in self.liststore:
                current_label = item[1]
                if current_label[:2] == '◎ ':
                    item[1] = current_label[2:]

            # Add marker on one item
            current_label = self.liststore[item_iter][1]
            if current_label[:2] != '◎ ':
                self.liststore[item_iter][1] = '◎ ' + current_label
