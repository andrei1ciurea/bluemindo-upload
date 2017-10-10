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

from common.sqlite import SQLite
from models.song import Song

class Album:
    """ Album() object """

    kind = 'album'

    def __init__(self, artist_name, album_name, songs_tree):
        """Initialization of the Album() model class.

        Usage:
         alb = Album('Artist', 'Album name', songs_tree)
        """

        self.__is_loaded = False

        # Try to load an Album() object with the artist, name and the tree.
        try:
            alb = songs_tree[artist_name][album_name]
        except KeyError:
            return self.__is_loaded

        self.__is_loaded = True

        alb.sort(key=lambda item: item[6])

        self.name = album_name
        self.artist = artist_name
        self.tracks = []
        self.statistics = self.__get_statistics()

        for sng in alb:
            self.tracks.append(Song(title=sng[0],
                                    artist=sng[1],
                                    album=sng[2],
                                    comment=sng[3],
                                    genre=sng[4],
                                    year=sng[5],
                                    track=sng[6],
                                    length=sng[7],
                                    filename=sng[8]
                              ))

    def __get_statistics(self):
        if self.__is_loaded:
            sql = SQLite()
            cur_nb = sql.execute('select * from stats_albums where ' +
                                 'album=:album', {'album': self.name})
            song = cur_nb.fetchone()

            if song is not None:
                times_played = song[1]
            else:
                times_played = 0

            sql.close()
            return times_played
        else:
            raise Exception('[Album] object was not loaded.')

    def increment_statistics(self):
        if self.__is_loaded:
            sql_insert = [
                'insert into stats_albums (album, tracks) values (?, ?)',
                [self.name, int(self.statistics + 1)]
            ]

            sql_update = [
                'update stats_albums set tracks=:value where album=:album',
                {'album': self.name, 'value': int(self.statistics + 1)}
            ]

            sql = SQLite()
            if self.statistics == 0:
                sql.execute(sql_insert[0], sql_insert[1])
            else:
                sql.execute(sql_update[0], sql_update[1])

            self.statistics = int(self.statistics + 1)

            sql.close()
        else:
            raise Exception('[Album] object was not loaded.')