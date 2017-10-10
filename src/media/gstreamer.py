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

from random import randrange
from urllib import request
from os.path import exists

from gi.repository import Gst as gst

class GStreamer(object):
    ref = None
    ref2 = None

    def __new__(cls, *args, **kws):
        # Singleton
        if cls.ref is None:
            cls.ref = object.__new__(cls)
        return cls.ref

    def __init__(self): 
        if GStreamer.ref2 is None: 
            GStreamer.ref2 = 42 
            self.nowplaying = None
            self.status = 'NULL'
            self.player = None

    def set_playback(self, playback):
        # Gstreamer initialization
        gst.init(None)
        self.playback = playback

        if self.player is None:
            self.player = gst.ElementFactory.make('playbin', 'bluemindo')

            bus = self.player.get_bus()
            bus.add_signal_watch()
            bus.connect('message', self.on_message)

            # ReplayGain
            if (gst.ElementFactory.find('rgvolume') and
                gst.ElementFactory.find('rglimiter')):
                self.audioconvert = gst.ElementFactory.make('audioconvert')

                self.rgvolume = gst.ElementFactory.make('rgvolume')
                self.rgvolume.set_property('album-mode', True)
                self.rgvolume.set_property('pre-amp', 0)
                self.rgvolume.set_property('fallback-gain', 0)

                self.rglimiter = gst.ElementFactory.make('rglimiter')
                self.rglimiter.set_property('enabled', True)

                self.rgfilter = gst.Bin()
                self.rgfilter.add(self.rgvolume)
                self.rgfilter.add(self.rglimiter)
                self.rgvolume.link(self.rglimiter)
                self.rgfilter.add_pad(gst.GhostPad.new('sink',
                                      self.rgvolume.get_static_pad('sink')))
                self.rgfilter.add_pad(gst.GhostPad.new('src',
                                      self.rglimiter.get_static_pad('src')))
                self.player.set_property('audio-filter', self.rgfilter)

    def playpause(self, song):
        # We want to pause the current song
        if song == None and self.status == 'PLAYING':
            self.player.set_state(gst.State.PAUSED)
            self.status = 'PAUSED'
            return self.status
        # We want to play the current song
        elif song == None and self.status == 'PAUSED':
            self.player.set_state(gst.State.PLAYING)
            self.status = 'PLAYING'
            return self.status
        # Nothing have been done
        elif song == None and self.status == 'NULL':
            self.status = 'NULL'
            return self.status
        # Huh, we can't do anything
        elif song == None and self.status == 'STOP':
            return 42
        else:
            # Launch this song
            if self.nowplaying is not None:
                self.stop()

            self.launch(song)
            return 'PLAYING'

    def stop(self):
        # Stop listening
        self.player.set_state(gst.State.NULL)
        self.nowplaying = None
        self.status = 'STOP'

    def launch(self, song):
        self.nowplaying = song

        # Launch a song by URI
        song = request.pathname2url(song)
        self.player.set_property('uri', 'file://' + song)

        self.player.set_state(gst.State.PLAYING)
        self.status = 'PLAYING'

    def getnow(self):
        return self.nowplaying

    def getstatus(self):
        return self.status

    def getplayer(self):
        return self.player

    def getposition(self):
        # Return the position in the song
        return self.player.query_position(gst.Format.TIME)[1]

    def seek(self, seconds):
        # Go to a position in the song
        value = int(gst.SECOND * seconds)
        self.player.seek_simple(gst.Format.TIME, gst.SeekFlags.FLUSH, value)

    def change_rg_mode(self, mode):
        if mode == 'album':
            self.rgvolume.set_property('album-mode', True)
        elif mode == 'track':
            self.rgvolume.set_property('album-mode', False)
        else:
            return

    def on_message(self, bus, message):
        # Handle Gstreamer messages
        if self.playback == 'gapless':
            return

        _type = message.type
        if _type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.status = 'NULL'

        elif _type == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            self.nowplaying = None
            self.status = 'NULL'
            err, debug = message.parse_error()
            print ('Error: %s' % err, debug)