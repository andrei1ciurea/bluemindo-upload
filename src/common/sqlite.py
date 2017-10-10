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

from os.path import join, exists
import sqlite3 as sqlite

from common.config import ConfigLoader
config = ConfigLoader()

class SQLite(object):
    def __init__(self): 
        sqlfile = join(config.datadir, 'songs.db')
        if not exists(sqlfile):
            database_exist = False
        else:
            database_exist = True

        self.cx = sqlite.connect(sqlfile)
        self.cur = self.cx.cursor()
        self.cx.text_factory = str

        if not database_exist:
            self.execute('create table songs ( '
                         'title text, '
                         'artist text, '
                         'album text, '
                         'comment text, '
                         'genre text, '
                         'year text, '
                         'track integer, '
                         'length integer, '
                         'filename text '
                         ')')

            self.execute('create table stats_songs ( '
                         'filename text, tracks integer )')

            self.execute('create table stats_albums ( '
                         'album text, tracks integer )')

            self.execute('create table stats_artists ( '
                         'artist text, tracks integer )')

    def execute(self, sql, param=None):
        if param is not None:
            self.cur.execute(sql, param)
        else:
            self.cur.execute(sql)

        self.cx.commit()
        return self.cur

    def executemany(self, sql, param):
        self.cur.executemany(sql, param)

        self.cx.commit()
        return self.cur

    def fetchall(self, cur):
        return cur.fetchall()

    def close(self):
        self.cur.close()
        self.cx.close()