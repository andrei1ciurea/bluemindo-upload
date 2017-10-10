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

from pickle import load
from os.path import join, isdir, isfile, realpath
from os import listdir, getcwd
from imp import find_module
from sys import path, exit

from common.functions import Functions

functions = Functions()

class ExtensionsLoader(object):	     
    def __init__(self): 
        # All available signals
        # If you think that we need another signal, please report a bug.
        # http://codingteam.net/project/bluemindo/bugs/add
        self.signals = {
            ##########
            # GLOBAL #
            ##########

            'OnBluemindoStarted': list(),
            # When Bluemindo is starting.
            # Args: glade and GTK objects

            'OnSongsTreeCreated': list(),
            # When the songs tree has been created.
            # Args: songs tree

            'OnBluemindoQuitted': list(),
            # When Bluemindo is exiting.

            ##########
            # PLAYER #
            ##########

            'AskPreviousSong': list(),
            # Sended to know what is the previous song.
            # REQUIRES 'OnPlayNewSong' or 'OnAbortPlayback' signal back!
            # current_song(title, artist, album, file) #TODO: Song()

            'AskNextSong': list(),
            # Sended to know what is the next song.
            # REQUIRES 'OnPlayNewSong' or 'OnAbortPlayback' signal back!
            # current_song(title, artist, album, file) #TODO: Song()

            'AskShuffleSong': list(),
            # Sended to know a random song.
            # REQUIRES 'OnPlayNewSong' signal back!

            ############
            # PLAYLIST #
            ############

            'OnSongQueued': list(),
            # When a new song is queued to the playlist.
            # Args: a Song() object

            'OnAlbumQueued': list(),
            # When a new album is queued to the playlist.
            # Args: an Album() object

            ############
            # PLAYBACK #
            ############

            'HasStartedSong': list(),
            # Send information about the song that is played.
            # Args: a Song() object

            'OnPlayNewSong': list(),
            # Send the song to be played.
            # Args: a Song() object

            'OnPlayNewAlbum': list(),
            # Send the album to be played.
            # Args: an Album() object

            'OnAbortPlayback': list(),
            # Send to abort playback.

            ####################
            # DBUS/API SIGNALS #
            ####################

            'OnPlayPressed': list(),
            # Send to request a play/pause action.

            'OnStopPressed': list(),
            # Send to request a stop button action.

            'OnNextPressed': list(),
            # Send to request a jump to next song.

            'OnPreviousPressed': list(),
            # Send to request a jump to previous song.
        }

        # Starting
        self.modules = []
        self.plugins = []
        self.conflist = {}
        self.is_in_config = False

    def load(self):
        """Load all modules and plugins"""

        # Load both modules and plugins
        exttype = 'modules'

        for file_ in listdir(exttype):
            # Get only modules without `.` as first
            # character (exclude .svn/)
            if (isdir(join(getcwd(), exttype, file_))
              and not file_.startswith('.') and not file_.startswith('__py')):
                name = file_.lower()

                # Try to load the module
                #try:
                if exttype in ('modules'):
                    module = __import__(''.join([exttype + '.', name]))
                    cls = getattr(getattr(module, name),
                                          name.capitalize())
                    obj = cls(self)
                else:
                    fp, pathname, desc = find_module(name)
                    if pathname.startswith(exttype):
                        module = __import__(name)
                        cls = getattr(module, name.capitalize())
                        obj = cls(self)
                    else:
                        continue

                if exttype == 'modules':
                    # Start the module
                    try:
                        obj.start_module()
                        self.modules.append(obj.module)
                    except:
                        pass

                #except Exception:
                #    print ("\n---------")
                #    print ('Extension `%s`, registered in *%s*, could not '
                #           'start.' % (file_, exttype) )
                #    print ("---------\n")

                #    if exttype == 'modules':
                #        print("Bluemindo's modules are required"
                #              " to launch the software.\nExiting.")
                #        #TODO: uncomment this.
                #        #exit()

    def connect(self, signal, function):
        """Connect a signal with a module's function"""

        if signal in self.signals:
            self.signals[signal].append(function)
        else:
            print ("`%s` don't exist." % signal)

    def load_event(self, signal, args=None):
        """Load an event, call related functions"""

        if signal in self.signals:
            dct = self.signals[signal]
            for dct_ in dct:
                if args is not None:
                    dct_(args)
                else:
                    dct_()
        else:
            print ("`%s` don't exist." % signal)

    def get_extensions(self):
        self.modules.sort((lambda x,y:cmp(x['name'], y['name'])))
        return {'modules': self.modules}