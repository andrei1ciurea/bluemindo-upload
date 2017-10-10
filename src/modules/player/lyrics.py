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
from urllib.parse import quote as urllib_quote
from urllib.error import HTTPError
from re import findall as re_findall, sub as re_sub, compile as re_compile
from os.path import isfile, join
from unicodedata import normalize
from bs4 import BeautifulSoup

from common.webservices import WebServices
from common.functions import Functions
from common.config import ConfigLoader

functions = Functions()

class LyricsDownloader:
    """A class to handles many lyrics websites."""

    def __init__(self):
        self.config = ConfigLoader()

    def get_lyrics(self, title, artist, no_download=False):
        """Return lyrics for a song."""
        song_hash = functions.get_hash(title, artist)
        lyrics_file = join(self.config.datadir, 'modules', 'lyrics',
                                                '%s.lyrics' % song_hash)
        lyrics = None

        if isfile(lyrics_file):
            # The lyrics already exists, return them
            file_ = open(lyrics_file)
            lyrics = file_.read()
            file_.close()
        elif not isfile(lyrics_file) and not no_download:
            # We need to download lyrics for this song
            lyricsmode = LyricsMode()
            lyrics = lyricsmode.get_lyrics(title, artist)
            if lyrics is None:
                lyricswikia = LyricsWikia()
                lyrics = lyricswikia.get_lyrics(title, artist)

            # Save the lyrics
            if lyrics is not None:
                file_ = open(lyrics_file, 'w')
                file_.write(lyrics)
                file_.close()

        # Return the lyrics
        return lyrics

class LyricsMode(WebServices):
    """Wrapper for LyricsMode.com."""

    def get_lyrics(self, title, artist):
        lyrics = ''

        artist = artist.replace(' ', '_').lower()
        artist = normalize('NFD', artist).encode('ascii', 'ignore')

        title = title.replace(' ', '_').lower()
        title = normalize('NFD', title).encode('ascii', 'ignore')

        url = ('http://www.lyricsmode.com/lyrics/%s/%s/%s.html' % (
               urllib_quote(artist.decode('utf-8'))[0],
               urllib_quote(artist.decode('utf-8')),
               urllib_quote(title.decode('utf-8'))))

        try:
            page = self.get_html(url)
        except HTTPError:
            page = ''

        clean_reg = re_compile('<.*?>')
        for txt in re_findall('(?s)<p id="lyrics_text" ' +
                              'class="ui-annotatable">(.*?)</p>', str(page)):
            txt = re_sub(clean_reg, '', txt)
            txt = txt.replace('\\\'', "'")
            txt = txt.replace('\\n', '\n')
            
            lyrics = txt

        if lyrics != '':
            return lyrics
        else:
            return None

class LyricsWikia(WebServices):
    """Wrapper for Lyrics.wikia.com"""

    def get_lyrics(self, title, artist):
        lyrics = ''

        artist = artist.replace(' ', '_')
        artist = normalize('NFD', artist).encode('ascii', 'ignore')

        title = title.replace(' ', '_')
        title = normalize('NFD', title).encode('ascii', 'ignore')

        url = ('http://lyrics.wikia.com/wiki/%s:%s' % (
               urllib_quote(artist.decode('utf-8')),
               urllib_quote(title.decode('utf-8'))))

        try:
            page = self.get_html(url)
        except HTTPError:
            page = ''

        soup = BeautifulSoup(page, 'html.parser')
        rew = soup.find('div', {'class': 'lyricbox'})

        if rew is None:
            return None
        else:
            for txt in re_findall('(?s)</script>(.*?)<!--', str(rew)):
                txt = txt.replace('<br/>', '\n')
                lyrics = txt

            if lyrics != '':
                return lyrics
            else:
                return None
