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

class Song:
    """ Song() object """

    kind = 'song'

    def __init__(self, **kwargs):
        """Initialization of the Song() model class.

        Usage:
         sng = Song(filename='/foo/whatever.flac')
        or:
         sng = Song(title='Foo', artist='Bar'…)
        """

        self.__is_loaded = False

        if 'filename' in kwargs.keys() and len(kwargs.keys()) == 1:
            filename = kwargs['filename']

            # Try to load a Song() object with the filename.
            sql = SQLite()
            cur_nb = sql.execute('select * from songs where filename=:file',
                                 {'file': filename})
            song_sql = cur_nb.fetchone()

            if song_sql is not None:
                self.__is_loaded = True

                self.title = song_sql[0]
                self.artist = song_sql[1]
                self.album = song_sql[2]
                self.track = song_sql[6]
                self.length = song_sql[7]
                self.comment = song_sql[3]
                self.genre = song_sql[4]
                self.year = song_sql[5]
                self.filename = song_sql[8]
                self.statistics = self.__get_statistics()

            sql.close()
        else:
            keys = ['title', 'artist', 'album', 'track', 'length', 'comment',
                    'genre', 'year', 'filename']

            for key in keys:
                if key not in kwargs.keys():
                    raise Exception('[Song] object was not mappable.')

            self.__is_loaded = True

            self.title = kwargs['title']
            self.artist = kwargs['artist']
            self.album = kwargs['album']
            self.track = kwargs['track']
            self.length = kwargs['length']
            self.comment = kwargs['comment']
            self.genre = kwargs['genre']
            self.year = kwargs['year']
            self.filename = kwargs['filename']
            self.statistics = self.__get_statistics()

    def __get_statistics(self):
        if self.__is_loaded:
            sql = SQLite()
            cur_nb = sql.execute('select * from stats_songs where ' +
                                 'filename=:file', {'file': self.filename})
            song = cur_nb.fetchone()

            if song is not None:
                times_played = song[1]
            else:
                times_played = 0

            sql.close()
            return times_played
        else:
            raise Exception('[Song] object was not loaded.')

    def increment_statistics(self):
        if self.__is_loaded:
            sql_insert = [
                'insert into stats_songs (filename, tracks) values (?, ?)',
                [self.filename, int(self.statistics + 1)]
            ]

            sql_update = [
                'update stats_songs set tracks=:value where filename=:file',
                {'file': self.filename, 'value': int(self.statistics + 1)}
            ]

            sql = SQLite()
            if self.statistics == 0:
                sql.execute(sql_insert[0], sql_insert[1])
            else:
                sql.execute(sql_update[0], sql_update[1])

            self.statistics = int(self.statistics + 1)

            sql.close()
        else:
            raise Exception('[Song] object was not loaded.')