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
from gi.repository.GObject import idle_add
from re import compile as re_compile
from os.path import join
from os import walk
from taglib import File as TagLibFile

from common.sqlite import SQLite

class MusicDatabase:
    def __init__(self, folder):
        self.folder = folder

        self.stored_result = []

    def do_scan(self, wdg=None):
        """This function scan the music directory."""
        songs = list()
        songs_filename = list()
        songs_artists = list()
        songs_albums = list()
        nb_song = 0
        fileregxp = re_compile('.+\.(flac|ogg|oga|mp3)$')

        # Walk in the music folder
        folder = self.folder

        song_files = list()
        for (dir_, rep, files) in walk(folder):
            for file_ in files:
                if fileregxp.match(file_):
                    nb_song += 1
                    song_files.append(join(dir_, file_))

        if wdg is not None:
            idle_add(wdg[0].set_text, _('Found %d songs.' % len(song_files)))
            idle_add(wdg[1].set_fraction, 0)

        id_song = 0
        ok_song = 0
        for song in song_files:
            id_song += 1

            try:
                exif = TagLibFile(song)
                if all(k in exif.tags.keys() for k in ('TITLE', 'ARTIST',
                                                       'ALBUM', 'TRACKNUMBER')):
                    ok_song += 1
                    filename = song

                    title = exif.tags['TITLE'][0]
                    artist = exif.tags['ARTIST'][0]
                    album = exif.tags['ALBUM'][0]
                    track = exif.tags['TRACKNUMBER'][0]

                    length = exif.length

                    if 'COMMENT' in exif.tags:
                        try:
                            comment = exif.tags['COMMENT'][0]
                        except IndexError:
                            comment = ''
                    else:
                        comment = ''

                    if 'GENRE' in exif.tags:
                        try:
                            genre = exif.tags['GENRE'][0]
                        except IndexError:
                            genre = ''
                    else:
                        genre = ''

                    if 'DATE' in exif.tags:
                        try:
                            year = exif.tags['DATE'][0]
                        except IndexError:
                            year = ''
                    else:
                        year = ''

                    if wdg is not None and id_song % 5:
                        idle_add(wdg[1].set_fraction, float(id_song) / float(nb_song))
                        idle_add(wdg[0].set_text, _('Added %d songs.' % id_song))

                    songs_filename.append(filename)
                    songs_artists.append(artist)
                    songs_albums.append(album)

                    songs.append((title, artist, album, comment, genre,
                                  year, track, length, filename))
                else:
                    raise OSError
            except OSError:
                idle_add(print, '[ERROR] Unable to import %s' % song)

        if wdg is not None:
            idle_add(wdg[0].set_text,
                     _('Metadata retrieved for %d songs. Updating database…' %
                     len(songs)))

        idle_add(print, '[RELOAD] Imported %d songs from %d founded.' %
                (ok_song, id_song))

        # Serialize songs
        sqlite = SQLite()
        sqlite.execute('delete from songs')
        sqlite.executemany('insert into songs (title, artist, album, '
                           'comment, genre, year, track, length, filename) '
                           'values (?, ?, ?, ?, ?, ?, ?, ?, ?)', songs)

        # Update songs
        cursor = sqlite.execute('select * from stats_songs')
        for song in cursor.fetchall():
            filename = song[0]

            if filename not in songs_filename:
                # Delete this songs from statistics
                sqlite.execute('delete from stats_songs where filename=:val',
                               {'val': filename})

        # Update artists
        cursor = sqlite.execute('select * from stats_artists')
        for artist in cursor.fetchall():
            artist = artist[0]

            if artist not in songs_artists:
                # Delete this artist from statistics
                sqlite.execute('delete from stats_artists where artist=:val',
                               {'val': artist})

        # Update albums
        cursor = sqlite.execute('select * from stats_albums')
        for album in cursor.fetchall():
            album = album[0]

            if album not in songs_albums:
                # Delete this album from statistics
                sqlite.execute('delete from stats_albums where album=:val',
                               {'val': album})

        # The job is ended o/
        sqlite.close()

    def scan(self, lbl, pbar):
        self.do_scan([lbl, pbar])

    def load(self, force_reload=False):
        if not force_reload and len(self.stored_result) > 0:
            # Return the already loaded songs
            return self.stored_result
        else:
            # Load the songs
            sqlite = SQLite()
            cursor = sqlite.execute('select * from songs order by '
                                    'artist, album, title')
            songs = cursor.fetchall()
            sqlite.close()

            return songs

    def artist_exists(self, artist_name):
        sqlite = SQLite()
        cursor = sqlite.execute('select count(*) from songs where artist=:val',
                                {'val': artist_name})
        songs = cursor.fetchall()
        sqlite.close()

        answer = songs[0][0]
        if answer > 0:
            return True

    def load_from_artist(self, artist_name):
        sqlite = SQLite()
        cursor = sqlite.execute('select * from songs where artist=:val ' +
                                ' order by album, title', {'val': artist_name})
        songs = cursor.fetchall()
        sqlite.close()

        return songs