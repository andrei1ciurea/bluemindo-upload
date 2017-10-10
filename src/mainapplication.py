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

from gi.repository.GObject import io_add_watch, idle_add, IO_IN
from socket import (socket, AF_UNIX, SOCK_DGRAM, SOCK_DGRAM,
                    error as socket_error)
from pickle import loads
from os.path import join
from os import getpid

try:
    from dbus import SessionBus, PROPERTIES_IFACE
    from dbus.service import (Object as dbusobj, method as dbus_method,
                              signal as dbus_signal)
    from dbus.mainloop.glib import DBusGMainLoop
    from dbus.types import Int64 as dbus_int64, Dictionary as dbus_dict
    import dbus.service as dbus_service

    OBJECT_NAME = 'org.mpris.MediaPlayer2.Bluemindo'
    INTERFACE_NAME = 'org.mpris.MediaPlayer2'
    INTERFACE_P_NAME = 'org.mpris.MediaPlayer2.Player'
    DBusGMainLoop(set_as_default=True)
except ImportError:
    OBJECT_NAME = False

from extensionsloader import ExtensionsLoader
from gui.mainwindow import MainWindow
from common.config import ConfigLoader
from common.functions import Functions

functions = Functions()
config = ConfigLoader()
extensions = ExtensionsLoader()

class MainApplication(object):
    def __init__(self):
        print ('The dolphin reaches the surface!')
        SOCKET_NAME = '/tmp/bluemindo'
        self.classes = []

        def handle_connection(source, condition):
            """This is the UNIX socket server."""
            datagram = server.recv(1024)
            argv = loads(datagram)
            usercommand = argv[1]

            # PlayPause, Play or Pause
            if usercommand in ('--playpause', '--play', '--pause'):
                idle_add(extensions.load_event, 'OnPlayPressed')

            # Stop
            elif usercommand == '--stop':
                idle_add(extensions.load_event, 'OnStopPressed')

            # Next
            elif usercommand == '--next':
                idle_add(extensions.load_event, 'OnNextPressed')

            # Previous
            elif usercommand == '--previous':
                idle_add(extensions.load_event, 'OnPreviousPressed')

            # Quit Bluemindo
            elif usercommand in ('--quit', '--plunge'):
                functions.close_bluemindo(None)

            # The command isn't handled by any action
            else:
                print ('Received unknown event `%s`!' % usercommand)

            return True

        # Create the UNIX socket server
        server = socket(AF_UNIX, SOCK_DGRAM)
        server.bind(SOCKET_NAME)
        io_add_watch(server, IO_IN, handle_connection)

        # Store current process identifier (PID)
        bluemindo_pid = getpid()
        pid_filename = join(config.datadir, 'pid')
        pid_file = open(pid_filename, 'w')
        pid_file.write(str(bluemindo_pid))
        pid_file.close()

        # Create the DBUS socket (MPRIS support)
        if OBJECT_NAME:
            bus = dbus_service.BusName(OBJECT_NAME, bus=SessionBus())
            MPRIS(self, bus)

        # Start user interface
        extensions.load()
        gui = MainWindow(extensions)

        # Nothing can be done after that
        gui.start_thread()


class MPRIS(dbusobj):

    def __init__(self, bluemindo, bus):
        self.bluemindo = bluemindo
        dbusobj.__init__(self, bus, '/org/mpris/MediaPlayer2')

        self.properties = [
            # Main
            'CanQuit',
            # Player
            'CanControl',
            'CanPause',
            'CanPlay',
            'CanSeek',
            'CanGoNext',
            'CanGoPrevious',
            'LoopStatus',
            'PlaybackStatus',
            'Metadata'
        ]

        self.playing = 'Stopped'
        self.song = None
        self.widgets = None

        def update_data(song):
            self.song = song
            self.playing = 'Playing'
            self.launch_dbus_signal(INTERFACE_P_NAME, ['PlaybackStatus',
                                                       'Metadata'])

        def play_pressed():
            if self.playing == 'Playing':
                self.playing = 'Paused'
            elif self.playing == 'Paused':
                self.playing = 'Playing'
            elif self.playing == 'Stopped':
                self.playing = 'Playing'

            self.launch_dbus_signal(INTERFACE_P_NAME, ['PlaybackStatus'])

        def stop_pressed():
            self.playing = 'Stopped'

            self.launch_dbus_signal(INTERFACE_P_NAME, ['PlaybackStatus'])

        def prevnext_pressed():
            self.playing = 'Playing'

            self.launch_dbus_signal(INTERFACE_P_NAME, ['PlaybackStatus'])

        def bluemindo_started(widgets):
            self.widgets = widgets

            self.launch_dbus_signal(INTERFACE_P_NAME, ['PlaybackStatus'])
            self.launch_dbus_signal(INTERFACE_NAME, ['CanQuit'])

        extensions.connect('HasStartedSong', update_data)
        extensions.connect('OnPlayPressed', play_pressed)
        extensions.connect('OnStopPressed', stop_pressed)
        extensions.connect('OnAbortPlayback', stop_pressed)
        extensions.connect('OnPreviousPressed', prevnext_pressed)
        extensions.connect('OnNextPressed', prevnext_pressed)
        extensions.connect('OnBluemindoStarted', bluemindo_started)

    # Properties methods

    @dbus_method(PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        return getattr(self, prop)

    @dbus_method(PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        props = {}
        for prop in self.properties:
            if prop != 'Metadata':
                props[prop] = getattr(self, prop)

        return dbus_dict(props, signature='sv', variant_level=1)

    @dbus_method(PROPERTIES_IFACE, in_signature='ssv')
    def Set(self, interface, prop, value):
        pass

    # Properties signals

    @dbus_signal(PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, updated, invalid):
        pass

    def launch_dbus_signal(self, interface, _props):
        props = {}
        for prop in _props:
            props[prop] = getattr(self, prop)

        self.PropertiesChanged(interface, props, [])

    # Main - Methods

    @dbus_method(INTERFACE_NAME, out_signature="s")
    def Identity(self):
        return 'Bluemindo'

    @dbus_method(INTERFACE_NAME, out_signature="s")
    def DesktopEntry(self):
        return 'bluemindo'

    @dbus_method(INTERFACE_NAME)
    def Quit(self):
        idle_add(functions.close_bluemindo, None)

    @dbus_method(INTERFACE_NAME, out_signature="(qq)")
    def MprisVersion(self):
        return (2, 2)

    # Main - Properties

    @property
    def CanQuit(self):
        return True

    # Player - Methods

    @dbus_method(INTERFACE_P_NAME)
    def PlayPause(self):
        idle_add(extensions.load_event, 'OnPlayPressed')

    @dbus_method(INTERFACE_P_NAME)
    def Play(self):
        idle_add(extensions.load_event, 'OnPlayPressed')

    @dbus_method(INTERFACE_P_NAME)
    def Pause(self):
        idle_add(extensions.load_event, 'OnPlayPressed')

    @dbus_method(INTERFACE_P_NAME)
    def Stop(self):
        idle_add(extensions.load_event, 'OnStopPressed')

    @dbus_method(INTERFACE_P_NAME)
    def Next(self):
        idle_add(extensions.load_event, 'OnNextPressed')

    @dbus_method(INTERFACE_P_NAME)
    def Previous(self):
        idle_add(extensions.load_event, 'OnPreviousPressed')

    @dbus_method(INTERFACE_NAME, in_signature="i")
    def PositionSet(self, millisec):
        print ('seek', millisec) #TODO: get this working!

    # Player - Properties

    @property
    def Metadata(self):
        if self.song is not None:
            metadata = {}

            title = self.song.title
            artist = self.song.artist
            album = self.song.album
            _file = self.song.filename
            length = self.song.length
            tracknumber = self.song.track

            filename = join(config.datadir, 'modules', 'player', 'covers',
                            functions.get_hash(album, artist))
            metadata['mpris:artUrl'] = 'file://' + filename

            metadata['xesam:album'] = album
            metadata['xesam:artist'] = artist
            metadata['xesam:title'] = title
            metadata['mpris:length'] = dbus_int64(length * (1/0.000001))
            metadata['xesam:trackNumber'] = tracknumber
            metadata['xesam:url'] = 'file://' + _file

            return dbus_dict(metadata, signature='sv', variant_level=1)

    @property
    def PlaybackStatus(self):
        return self.playing

    @property
    def LoopStatus(self):
        return 'Playlist'

    @property
    def CanControl(self):
        return True

    @property
    def CanGoNext(self):
        return True

    @property
    def CanGoPrevious(self):
        return True

    @property
    def CanPause(self):
        return True

    @property
    def CanPlay(self):
        return True

    @property
    def CanSeek(self):
        return True