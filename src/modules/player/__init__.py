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
from gi.repository.GObject import idle_add, timeout_add
from gi.repository.Gio import ThemedIcon
from gi.repository.Gtk import (Image, IconSize, Builder as gtk_builder,
                               Popover, ScrolledWindow, TextView, TextBuffer,
                               Spinner, Box)
from gi.repository.GdkPixbuf import Pixbuf
from os.path import join, isfile, exists
from os import remove as os_remove
from threading import Thread

from common.functions import Functions
from common.config import ConfigLoader
from media.gstreamer import GStreamer
from modules.player.lyrics import LyricsDownloader

class Player:
    def __init__(self, extensionsloader):
        self.extensions = extensionsloader
        self.module = {'name': 'Player'}
        self.config = {}

        self.functions = Functions()
        self.userconf = ConfigLoader()

        self.lyrics_downloader = LyricsDownloader()

        def start_playback(wdg):
            # Create GStreamer instance
            self.gst = GStreamer()
            self.gst.set_playback('gapless')
            self.gst.player.connect('about-to-finish', self.song_nearly_ended)
            self.gst.stop()

            self.current_song = False
            self.current_album = False

            # Prepare buttons
            self.btn_playpause = wdg[0][7]
            self.btn_previous = wdg[0][5]
            self.btn_next = wdg[0][8]
            self.btn_stop = wdg[0][6]

            self.btn_previous.connect('clicked', self.previous_pressed)
            self.btn_stop.connect('clicked', self.stop_pressed)
            self.btn_playpause.connect('clicked', self.play_pressed)
            self.btn_next.connect('clicked', self.next_pressed)

            self.btn_player = wdg[0][9]
            self.headerbar = wdg[0][0]

            # Create the player box and popover
            gtkpla = join(self.functions.datadir, 'glade', 'playerbar.ui')
            win = gtk_builder()
            win.set_translation_domain('bluemindo')
            win.add_from_file(gtkpla)
            basebox = win.get_object('playerbox')
            wdg[0][0].add(basebox)

            self.player_event = win.get_object('player_event')
            self.player_event.set_size_request(32, 32)
            self.player_button_img = win.get_object('image_cover')
            self.player_event.connect('button-press-event', self.show_player)
            default = join(self.functions.datadir, 'image', 'logo_head_big.png')
            cover_px = Pixbuf.new_from_file_at_scale(default, 20, 20, True)
            self.player_button_img.set_from_pixbuf(cover_px)
            self.player_event.set_sensitive(False)

            self.player_scalab = win.get_object('label_scale')
            self.player_scalab.set_markup('<span size="small">00:00</span>')
            self.player_sca = win.get_object('scale')
            self.player_sca.connect('change-value', self.on_change_value)
            self.player_sca.set_sensitive(False)

            # Create the player popover
            gtkpla = join(self.functions.datadir, 'glade', 'playerpopover.ui')
            win = gtk_builder()
            win.add_from_file(gtkpla)
            hbox = win.get_object('box-player')

            self.player_img = win.get_object('image')
            self.player_pop = Popover.new(self.player_event)
            self.player_pop.set_size_request(200, 200)
            self.player_pop.add(hbox)

            self.lyrics_button = wdg[1].get_object('tool-lyrics')
            self.lyrics_pop = Popover.new(self.lyrics_button)
            self.lyrics_pop.set_size_request(400, 600)
            box = Box(1, 0)
            self.lyrics_swin = ScrolledWindow()
            lyrics_tview = TextView()
            lyrics_tview.set_editable(False)
            self.lyrics_buffer = TextBuffer()
            lyrics_tview.set_buffer(self.lyrics_buffer)
            self.lyrics_swin.add(lyrics_tview)
            box.add(self.lyrics_swin)
            self.lyrics_wait = Spinner()
            self.lyrics_wait.props.active = True
            box.add(self.lyrics_wait)
            self.lyrics_pop.add(box)

            def show_lyrics(widget):
                if self.current_song:
                    title = self.current_song.title
                    artist = self.current_song.artist
                    album = self.current_song.album
                    filename = self.current_song.filename

                    sn = self.functions.get_hash(title, artist)
                    lyrics_file = join(self.userconf.datadir, '%s.lyrics' % sn)

                    lyrics = self.lyrics_downloader.get_lyrics(title,
                                                               artist,
                                                               True)

                    self.lyrics_pop.show_all()

                    if lyrics is not None:
                        self.lyrics_wait.hide()
                        self.lyrics_swin.show()
                        self.lyrics_buffer.set_text(lyrics)
                    else:
                        self.lyrics_swin.hide()
                        self.lyrics_wait.show()
                        self.lyrics_buffer.set_text('')

            self.lyrics_button.connect('clicked', show_lyrics)
            self.lyrics_button.set_sensitive(False)

        # Acquire the songs tree
        def acquire_tree(st):
            self.songs_tree = st

        self.extensions.connect('OnSongsTreeCreated', acquire_tree)
        self.extensions.connect('OnBluemindoStarted', start_playback)
        self.extensions.connect('OnPlayNewSong', self.on_play_new_song)
        self.extensions.connect('OnPlayNewAlbum', self.on_play_new_album)
        self.extensions.connect('OnAbortPlayback', self.on_abort_playback)

        self.extensions.connect('OnPlayPressed', self.play_pressed)
        self.extensions.connect('OnStopPressed', self.stop_pressed)
        self.extensions.connect('OnNextPressed', self.next_pressed)
        self.extensions.connect('OnPreviousPressed', self.previous_pressed)


    def previous_pressed(self, wdg=None):
        if self.current_album:
            # We are listening an album: move to previous song
            album_items = len(self.current_album.tracks) - 1
            a = -1
            for sng in self.current_album.tracks:
                a += 1
                if sng.track == self.current_song.track:
                   item_in_album = a

            if item_in_album > 0:
                self.on_play_new_song(self.current_album.tracks[item_in_album - 1])
            else:
                self.stop_pressed(None)
        else:
            # We were a listening to a single song, try to ask another one
            self.extensions.load_event('AskPreviousSong', self.current_song)

    def stop_pressed(self, wdg=None):
        # Aborting playback
        cur = self.gst.getnow()
        self.gst.stop()

        # Update global vars
        self.current_song = False
        self.current_album = False

        # Update file
        current_playing = join(self.userconf.datadir, 'current-playing')
        if exists(current_playing):
            os_remove(current_playing)

        # Update user interface
        self.btn_playpause.set_image(Image.new_from_gicon(ThemedIcon(
             name='media-playback-start-symbolic'), IconSize.BUTTON))

        self.headerbar.props.subtitle = ''

        default = join(self.functions.datadir, 'image', 'logo_head_big.png')
        cover_px = Pixbuf.new_from_file_at_scale(default, 20, 20, True)
        self.player_button_img.set_from_pixbuf(cover_px)
        self.player_event.set_sensitive(False)
        self.lyrics_button.set_sensitive(False)
        self.player_sca.set_sensitive(False)

        # Do we have to send the signal?
        if wdg is not None:
            self.extensions.load_event('OnStopPressed')

    def play_pressed(self, wdg=None):
        # Get GStreamer status, don't do anything if playser is stopped
        first_state = self.gst.getstatus()
        if first_state == 'STOP':
            return

        # Toggles play/pause
        self.gst.playpause(None)
        new_state = self.gst.getstatus()

        # Update user interface
        if new_state == 'PAUSED':
            self.btn_playpause.set_image(Image.new_from_gicon(ThemedIcon(
                 name='media-playback-start-symbolic'), IconSize.BUTTON))
        else:
            self.btn_playpause.set_image(Image.new_from_gicon(ThemedIcon(
                 name='media-playback-pause-symbolic'), IconSize.BUTTON))        

    def next_pressed(self, wdg=None):
        if self.current_album:
            # We are listening an album: move to next song
            album_items = len(self.current_album.tracks) - 1
            a = -1
            for sng in self.current_album.tracks:
                a += 1
                if sng.track == self.current_song.track:
                   item_in_album = a

            if item_in_album < album_items:
                self.on_play_new_song(self.current_album.tracks[item_in_album + 1])
            else:
                self.stop_pressed(None)
        else:
            # We were a listening to a single song, try to ask another one
            self.extensions.load_event('AskNextSong', self.current_song)

    def on_abort_playback(self):
        self.stop_pressed(None)

    def on_play_new_song(self, song):
        # Guess ReplayGain mode
        if hasattr(song, 'rg_mode_guess') and song.rg_mode_guess == 'album':
            self.gst.change_rg_mode('album')
        else:
            if not self.current_album:
                self.gst.change_rg_mode('track')
            else:
                if song in self.current_album.tracks:
                    self.gst.change_rg_mode('album')
                else:
                    self.current_album = False
                    self.gst.change_rg_mode('track')

        # Play the song
        cur = self.gst.getnow()
        self.gst.playpause(song.filename)

        # Update global vars
        self.current_song = song

        # Update user interface
        self.btn_playpause.set_image(Image.new_from_gicon(ThemedIcon(
             name='media-playback-pause-symbolic'), IconSize.BUTTON))

        title = song.title
        artist = song.artist
        album = song.album
        filename = song.filename

        self.headerbar.props.subtitle = title + ' - ' + artist

        default = join(self.functions.datadir, 'image', 'logo_head_big.png')
        bdir = join(self.userconf.datadir, 'modules', 'player', 'covers')
        cover = join(bdir, self.functions.get_hash(album, artist))
        if isfile(cover):
            cover_px = Pixbuf.new_from_file_at_scale(cover, 32, 32, True)
        else:
            cover_px = Pixbuf.new_from_file_at_scale(default, 20, 20, True)

        self.player_button_img.set_from_pixbuf(cover_px)
        self.player_event.set_sensitive(True)
        self.lyrics_button.set_sensitive(True)

        # Update file
        current_playing = join(self.userconf.datadir, 'current-playing')
        file_ = open(current_playing, 'w')
        file_.write(title + ' - ' + artist + ' (from: ' + album + ')')
        file_.close()

        # Update player informations
        if isfile(cover):
            cover_px = Pixbuf.new_from_file_at_scale(cover, 200, 200, True)
        else:
            cover_px = Pixbuf.new_from_file_at_scale(default, 120, 120, True)
        self.player_img.set_from_pixbuf(cover_px)

        # Create the scale
        self.player_sca.set_sensitive(True)
        self.player_sca.set_range(0, float(song.length))
        timeout_add(500, self.scale_timer)

        # Download lyrics
        thread = Thread(group=None, target=self.lyrics_downloader.get_lyrics,
                        name='lyrics', args=(title, artist))
        thread.start()

        # Send notification to extensions about this new song
        self.extensions.load_event('HasStartedSong', song)

    def on_play_new_album(self, album):
        self.current_album = album
        self.on_play_new_song(album.tracks[0])

    def song_nearly_ended(self, *args):
        idle_add(self.next_pressed, True)

    def show_player(self, widget, ka):
        self.player_pop.show_all()

    def scale_timer(self):
        pos = self.gst.getposition()
        position = int(self.gst.getposition() / 1000000000)
        self.player_scalab.set_markup('<span size="small">' +
                                      self.functions.human_length(position) +
                                      '</span>')
        self.player_sca.set_value(position)
        return True

    def on_change_value(self, widget, scroll, value):
        seconds = int(value)
        self.gst.seek(seconds)
