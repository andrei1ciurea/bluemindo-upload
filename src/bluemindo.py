#!/usr/bin/env python3
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

from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0')
gi_require_version('Gst', '1.0')

from os.path import isfile, exists
from os import getpid
from locale import (setlocale as locale_setlocale, bindtextdomain as
                    locale_bindtextdomain)
from gettext import (bindtextdomain, textdomain, bind_textdomain_codeset,
                     gettext as _)

if isfile('../locale/bluemindo.pot'):
    localedir = '../locale'
else:
    localedir = '/usr/share/locale'

locale_bindtextdomain('bluemindo', localedir)
bindtextdomain('bluemindo', localedir)
textdomain('bluemindo')
bind_textdomain_codeset('bluemindo', 'UTF-8')

from gi.repository.Gtk import (Dialog, Label, STOCK_CANCEL, STOCK_OK,
                               ResponseType)

from socket import socket, AF_UNIX, SOCK_DGRAM, error as socket_error
from pickle import dumps
from sys import argv
from os import remove
from os.path import join

from common.config import ConfigLoader
from common.functions import Functions
config = ConfigLoader()
functions = Functions()

class Bluemindo(object):
    def __init__(self):
        SOCKET_NAME = '/tmp/bluemindo'

        if len(argv) > 1 and argv[1] in ('-h', '--help'):
            # Show the help
            print(_("Bluemindo  Copyright (C) 2007-2016  Erwan Briand\n"
                    "This program comes with ABSOLUTELY NO WARRANTY.\n"
                    "This is free software, and you are welcome to\n"
                    "redistribute it under certain conditions.\n\n"
                    "Usage: bluemindo[.py] [options]\n\n"
                    "Available options:\n"
                    "--current\t\t"
                     "Show the current playing song artist, title and album\n"
                    "--current-cover\t\t"
                     "Show the path to the cover of the current playing song\n"
                    "--current-lyrics\t"
                     "Show the lyrics for the current playing song\n\n"
                    "--playpause, --play, --pause\t"
                     "Play or pause a song\n"
                    "--stop\t\t\t"
                     "Stop a song\n"
                    "--previous\t\t"
                     "Jump to the previous song in playlist\n"
                    "--next\t\t\t"
                     "Jump to the next song in playlist\n\n"
                    "--quit, --plunge\t"
                     "Quit Bluemindo"))

        elif len(argv) > 1 and argv[1] == '--bluemindo':
            print('                                   __            ')
            print('                               _.-~  )           ')
            print('                    _..--~~~~,\'   ,-/     _     ')
            print('                 .-\'. . . .\'   ,-\',\'    ,\' )')
            print('               ,\'. . . _   ,--~,-\'__..-\'  ,\' ')
            print('             ,\'. . .  (@)\' ---~~~~      ,\'    ')
            print('            /. . . . \'~~             ,-\'       ')
            print('           /. . . . .             ,-\'           ')
            print('          ; . . . .  - .        ,\'              ')
            print('         : . . . .       _     /                 ')
            print('        . . . . .          `-.:                  ')
            print('       . . . ./  - .          )                  ')
            print('      .  . . |  _____..---.._/ _____⋅~~~~`_      ')
            print('~---~~~~----~~~~             ~~            ~~~~~~')

        elif len(argv) > 1 and argv[1].startswith('--current'):
            # Get the current song
            current_playing = join(config.datadir, 'current-playing')
            if exists(current_playing):
                file_ = open(current_playing)
                csong = file_.read()
                csong_ = csong.split(' (from: ')
                calbum = csong_[1][:-1]

                csong_ = csong_[0].split(' - ')
                ctitle = csong_[0]
                cartist = csong_[1]
                file_.close()

                # Send the current playing song album cover
                if argv[1].endswith('-cover'):
                    file_ = join(config.datadir, 'modules', 'player', 'covers',
                            functions.get_hash(calbum, cartist))
                    if isfile(file_):
                        print(file_)
                    else:
                        print('File not found.')

                # Send the current playing song lyrics
                elif argv[1].endswith('-lyrics'):
                    file_ = join(config.datadir, 'modules', 'lyrics',
                            functions.get_hash(ctitle, cartist) + '.lyrics')
                    if isfile(file_):
                        lyric = open(file_)
                        print(lyric.read())
                        lyric.close()
                    else:
                        print('File not found.')

                # Send the current playing song artist and title
                else:
                    print(csong)

        elif len(argv) > 1 and exists(SOCKET_NAME):
            # Create a client and connect to the UNIX socket in
            # order to send the user's request
            try:
                client = socket(AF_UNIX, SOCK_DGRAM)
                client.connect_ex(SOCKET_NAME)
                client.send(dumps(argv))
                client.close()
            except socket_error:
                print('Socket error.')

        elif len(argv) > 1 and not exists(SOCKET_NAME):
            # We cannot do anything here
            print('Socket not found.')

        elif len(argv) == 1 and exists(SOCKET_NAME):
            # The socket exists but we want to start Bluemindo: it fails
            print ('Warning: found an existing Bluemindo socket!')

            pid_filename = join(config.datadir, 'pid')
            if isfile(pid_filename):
                # Get PID connected with the existing socket 
                pid_filename = join(config.datadir, 'pid')
                pid_file = open(pid_filename, 'r')
                pid_stored = pid_file.read()
                pid_file.close()

                bluemindo_pid = getpid()
                if bluemindo_pid != pid_stored:
                    print('Socket reset. Launching Bluemindo anyway.')

                    # Store current process identifier (PID)
                    pid_file = open(pid_filename, 'w')
                    pid_file.write(str(bluemindo_pid))
                    pid_file.close()

                    # Remove the existing socket
                    remove(SOCKET_NAME)
                    if isfile(join(config.datadir, 'lock')):
                        remove(join(config.datadir, 'lock'))

                    from mainapplication import MainApplication
                    MainApplication()
        else:
            # Start Bluemindo
            from mainapplication import MainApplication
            MainApplication()

def main():
    bluemindo = Bluemindo()

if __name__ == "__main__":
    main()