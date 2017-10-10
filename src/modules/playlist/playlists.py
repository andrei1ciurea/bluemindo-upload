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

from os.path import join, isdir, isfile, basename, exists
from os import makedirs, listdir, remove

from common.config import ConfigLoader
config = ConfigLoader()

class Playlists:
    """This class can create, delete and manager m3u-like playlists.
       Documentation: http://en.wikipedia.org/wiki/M3U
       This class handles playlists in unicode: m3u8"""

    def __init__(self):
        self.datadir = join(config.datadir, 'modules', 'explorer', 'playlists')
        if not isdir(self.datadir):
            makedirs(self.datadir)

    # This function returns the list of all Bluemindo's saved playlists
    def get_playlists(self):
        dir_list = listdir(self.datadir)

        files = []
        for filename in dir_list:
            if filename.endswith('.m3u8'):
                pretty = filename.split('.m3u8')
                files.append(pretty[0])

        return files

    # This function creates a new playlist
    def create_new_playlist(self, name):
        filename = join(self.datadir, str(name) + '.m3u8')

        if not exists(filename):
            playlist_file = open(filename, 'w')
            playlist_file.close()
            return True

    # This function deletes a playlist
    def delete_playlist(self, name):
        playlist_file = join(self.datadir, name + '.m3u8')

        if isfile(playlist_file):
            remove(playlist_file)

    # This function loads a playlist
    def load_playlist(self, name):
        playlist_file = open(join(self.datadir, name + '.m3u8'), 'r')
        songs = playlist_file.readlines()
        playlist_file.close()

        clean_songs = []
        for song in songs:
            clean_songs.append(song.replace('\n', ''))

        return clean_songs

    # This function writes a playlist
    def write_playlist(self, name, songs):
        playlist_file = open(join(self.datadir, str(name) + '.m3u8'), 'w')

        for song in songs:
            if hasattr(song, 'filename'):
                playlist_file.write(song.filename + '\n')

        playlist_file.close()
