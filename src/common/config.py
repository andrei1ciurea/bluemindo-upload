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

from os.path import join, isdir, isfile, expanduser, exists
from os import listdir, makedirs, environ, removedirs
from pickle import dump
import configparser

class ConfigLoader(object):
    ref = None
    ref2 = None

    def __new__(cls, *args, **kws):
        # Singleton
        if cls.ref is None:
            cls.ref = object.__new__(cls)
        return cls.ref

    def __init__(self):
        if ConfigLoader.ref2 is None:
            ConfigLoader.ref2 = 42
            self.launch()

    def launch(self):
        self.config = configparser.ConfigParser()

        # Set the configuration directory to XDG_CONFIG_HOME if exists
        # If not, set it to $HOME/.config/bluemindo
        # http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
        if environ.get('XDG_CONFIG_HOME'):
            self.confdir = join(environ.get('XDG_CONFIG_HOME'), 'bluemindo')
        else:
            self.confdir = join(expanduser('~'), '.config', 'bluemindo')

        if not isdir(self.confdir):
            makedirs(self.confdir)

        # Set the data directory to XDG_DATA_HOME if exists
        # If not, set it to $HOME/.local/share/bluemindo
        # http://standards.freedesktop.org/basedir-spec/basedir-spec-0.6.html
        if environ.get('XDG_DATA_HOME'):
            self.datadir = join(environ.get('XDG_DATA_HOME'), 'bluemindo')
        else:
            self.datadir = join(expanduser('~'), '.local', 'share', 'bluemindo')

        if not isdir(self.datadir):
            makedirs(self.datadir)

        # Create folders
        dirs = [join(self.datadir, 'modules', 'explorer', 'artists'),
                join(self.datadir, 'modules', 'explorer', 'playlists'),
                join(self.datadir, 'modules', 'explorer', 'artists'),
                join(self.datadir, 'modules', 'lyrics'),
                join(self.datadir, 'modules', 'player', 'covers')
        ]
        for createdir in dirs:
            if not exists(createdir):
                makedirs(createdir)

        # Retrieve configuration file
        default_configuration = {
            'Explorer': {'folder':          '',
                         # Set folder to your music directory.
                         'scan_at_startup': int(False)
                         # True if you want to check for new songs at launch.
                        },
            'Playlist': {'repeat':          int(True),
                         # True to enable repeat mode.
                         'shuffle':         int(True),
                         # True to enable shuffle mode when playlist is empty.
                         'shuffle_mode':    'random'
                         # Available shuffle modes are: random and similar.
                        },
            'Window':   {'y':               0,
                         'x':               0,
                         'height':          900,
                         'width':           1150
                         # Last saved position and size of the window.
                        }
        }

        config_file = join(self.confdir, 'bluemindo.cfg')
        if isfile(config_file):
            # Load global Bluemindo configuration file
            self.config.read(config_file)
        else:
            self.config.write(open(config_file, 'w'))

        # Create or update global Bluemindo configuration file
        for module in default_configuration:
            if not self.config.has_section(module):
                self.config.add_section(module)

            option = default_configuration[module]
            for key in option:
                if not self.config.has_option(module, key):
                    self.config.set(module, key, str(option[key]))

        # Save configuration file
        self.config.write(open(config_file, 'w'))

        # Store the Bluemindo key for the Last.fm API
        # Don't use it, create your own here: http://www.lastfm.fr/api/account
        self.lastfm_key = 'MjZjOTgyYzk4NTVkZjcxMTIwMTgzY2UzZmJiNmI5ODA='

    def update_key(self, module, key, value):
        config_file = join(self.confdir, 'bluemindo.cfg')
        self.config.set(module, key, value)
        self.config.write(open(config_file, 'w'))