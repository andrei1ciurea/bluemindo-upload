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

from io import StringIO
from os.path import join, exists
from os import makedirs, remove
from re import compile as re_compile
from base64 import b64decode
from urllib.request import urlopen, urlretrieve
from urllib.parse import quote
from urllib.error import HTTPError
from threading import Lock
from time import time, sleep
import xml.etree.cElementTree as ElementTree

from common.config import ConfigLoader
from common.functions import Functions

class WebServices(object):
    """A class to handles many WebServices."""

    config = ConfigLoader()
    functions = Functions()
    lock = Lock()

    def get_xml(self, url):
        """This function downloads a file and returns an ElementTree object."""
        req = urlopen(url)
        content = req.read()

        return ElementTree.fromstring(content)

    def get_html(self, url):
        """This function downloads a file and returns its content."""
        req = urlopen(url)
        content = req.read()

        return content


class LastFm(WebServices):
    """A class for Last.fm."""

    def __init__(self):
        self.api_key = b64decode(self.config.lastfm_key)
        self.api_url = 'http://ws.audioscrobbler.com/2.0/'

    def get_similar_artists(self, artist_name):
        """Get a list of similar artists."""
        url = (self.api_url + '?method=artist.getsimilar&artist=%s&api_key=%s' %
              (quote(str(artist_name)), quote(self.api_key)))

        artists_list = []

        tree = self.get_xml(url)
        xml = tree.find('similarartists')
        artists = xml.findall('artist')

        for artist in artists:
            name = artist.find('name') 
            artists_list.append(name.text)

        return artists_list

    def get_artists_pictures(self, artists):
        """Get a picture for all artists."""
        print ('[ARTIST_PICTURES] downloading %d artists' % len(artists))
        for artist in artists:
            self.get_artist_picture(artist)
            sleep(2)

    def get_artist_picture(self, artist_name):
        """Get a picture for an artist."""
        url = (self.api_url + '?method=artist.getinfo&artist=%s&api_key=%s' %
              (quote(str(artist_name)), quote(self.api_key)))

        datadir = self.config.datadir
        hash_a = self.functions.get_hash(artist_name, 'picture')
        pictures_dir = join(datadir, 'modules', 'explorer', 'artists')
        artist_file = join(pictures_dir, hash_a)

        self.lock.acquire()
        try:
            if not exists(pictures_dir):
                makedirs(pictures_dir)
        finally:
            self.lock.release()

        if not exists(artist_file):
            try:
                tree = self.get_xml(url)

                artist = tree.find('artist')
                images = artist.getiterator('image')
                for img in images:
                    if img.attrib['size'] == 'large':
                        artist_image = img.text
                        if artist_image is not None:
                            print ('[RETRIEVED] artist_downloading '+
                                   artist_name)
                            urlretrieve(artist_image, artist_file)
                            return artist_file
            except HTTPError:
                print ('[HTTPError] artist_downloading ' + artist_name)
        else:
            return artist_file

    def get_albums_pictures(self, albums):
        """Get a picture for all albums."""
        print ('[ALBUM_PICTURES] downloading %d albums' % len(albums))
        for album in albums:
            self.get_album_picture(album[0], album[1])
            sleep(2)

    def get_album_picture(self, artist_name, album_name):
        """Get a picture for an album."""
        url = (self.api_url +
               '?method=album.getinfo&artist=%s&album=%s&api_key=%s' %
                  (quote(str(artist_name)),
                   quote(str(album_name)),
                   quote(self.api_key)
                  ))
        datadir = self.config.datadir
        hash_a = self.functions.get_hash(album_name, artist_name)
        pictures_dir = join(datadir, 'modules', 'player', 'covers')
        album_file = join(pictures_dir, hash_a)

        self.lock.acquire()
        try:
            if not exists(pictures_dir):
                makedirs(pictures_dir)
        finally:
            self.lock.release()

        if not exists(album_file):
            try:
                tree = self.get_xml(url)

                album = tree.find('album')
                images = album.getiterator('image')
                for img in images:
                    if img.attrib['size'] == 'mega':
                        album_image = img.text
                        if album_image is not None:
                            print ('[RETRIEVED] cover_downloading '+
                                   artist_name, album_name)
                            urlretrieve(album_image, album_file)
                            return album_file
            except HTTPError:
                print ('[HTTPError] cover_downloading ' + artist_name, album_name)
        else:
            return album_file