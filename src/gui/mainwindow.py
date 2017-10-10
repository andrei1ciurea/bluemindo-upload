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
from gi.repository.GObject import threads_init

from gi.repository.GdkPixbuf import Pixbuf
from gi.repository.Gtk import (main as gtk_main, Window, IconSize, Image,
                               Button, Builder as gtk_builder, HeaderBar, Box,
                               Orientation, StyleContext, AboutDialog)
from gi.repository.Gio import ThemedIcon
from os.path import join
from os import getcwd

from common.config import ConfigLoader
from common.functions import Functions
functions = Functions()
config = ConfigLoader()

class MainWindow(object):
    def __init__(self, extensions):
        # Start threads
        threads_init()

        self.extensions = extensions

        # Create the main Bluemindo window
        self.main_window = Window()
        functions.open_bluemindo(self.main_window)

        # Handling close button
        def close_window(wdg, ka):
            functions.close_bluemindo(self.main_window, True)

        self.main_window.connect('delete_event', close_window)

        # Create the whole Header Bar
        box = HeaderBar()
        box.set_show_close_button(True)
        box.props.title = 'Bluemindo'
        self.main_window.set_titlebar(box)

        # Add an icon to the window
        icon_file = join(functions.datadir, 'image', 'logo_head_small.png')
        pixbuf = Pixbuf.new_from_file(icon_file)
        self.main_window.set_icon(pixbuf)

        # Add the about button
        about_button = Button(relief=2)
        about_button.add(Image.new_from_gicon(ThemedIcon(
                              name='help-about-symbolic'), IconSize.BUTTON))
        box.pack_end(about_button)

        # Add the reload button
        refresh_button = Button(relief=2)
        refresh_button.add(Image.new_from_gicon(ThemedIcon(
                              name='view-refresh-symbolic'), IconSize.BUTTON))
        box.pack_end(refresh_button)

        # Add PREVIOUS/STOP/PLAYPAUSE/NEXT buttons
        player_box = Box(orientation=Orientation.HORIZONTAL)
        StyleContext.add_class(player_box.get_style_context(), 'linked')

        previous_b = Button()
        previous_b.set_size_request(42, -1)
        previous_b.add(Image.new_from_gicon(ThemedIcon(
                       name='media-skip-backward-symbolic'), IconSize.BUTTON))
        player_box.add(previous_b)

        stop_b = Button()
        stop_b.set_size_request(42, -1)
        stop_b.add(Image.new_from_gicon(ThemedIcon(
                       name='media-playback-stop-symbolic'), IconSize.BUTTON))
        player_box.add(stop_b)

        playpause_b = Button()
        playpause_b.set_size_request(55, -1)
        playpause_b.add(Image.new_from_gicon(ThemedIcon(
                       name='media-playback-start-symbolic'), IconSize.BUTTON))
        player_box.add(playpause_b)

        next_b = Button()
        next_b.set_size_request(42, -1)
        next_b.add(Image.new_from_gicon(ThemedIcon(
                       name='media-skip-forward-symbolic'), IconSize.BUTTON))
        player_box.add(next_b)

        box.pack_start(player_box)

        # Create the main window
        glade_main = join(functions.datadir, 'glade', 'mainwindow.ui')
        win = gtk_builder()
        win.set_translation_domain('bluemindo')
        win.add_from_file(glade_main)

        self.main_window.add(win.get_object('box1'))

        # Connect to the about button
        def show_dialog(wdg):
            dialog = AboutDialog()
            dialog.set_transient_for(self.main_window)

            dialog.set_artists(['Thomas Julien <terr1enrun@gmail.com>'])
            dialog.set_authors(['Erwan Briand <erwan@codingteam.net>',
                                'Vincent Berset <msieurhappy@gmail.com>',
                                'Thibaut Girka <thibaut.girka@gmail.com>',
                                'Ľubomír Remák <lubomirr88@gmail.com>',
                                'Anaël Verrier <elghinn@free.fr>'])
            dialog.set_translator_credits(
                            'Bruno Conde <blconde@gmail.com>\n' +
                            'Niklas Grahn <terra.unknown@yahoo.com>\n' +
                            'Ľubomír Remák <lubomirr88@gmail.com>\n' +
                            'Salvatore Tomarchio <tommyx_x@yahoo.it>\n' +
                            'Shang Yuanchun <05281253@bjtu.edu.cn>'
                        )

            dialog.set_copyright('Copyright © 2007-2016 Erwan Briand ' +
                                 '<erwan@codingteam.net>')

            dialog.set_comments(_('Ergonomic and modern music player ' +
                                  'designed for audiophiles.'))

            dialog.set_license('GNU General Public License (v3)')
            dialog.set_license_type(10)

            dialog.set_program_name('Bluemindo')
            dialog.set_version('1.0RC1')
            dialog.set_website('http://bluemindo.codingteam.net')

            pxbf = Pixbuf.new_from_file_at_scale(join(functions.datadir,
                          'image', 'logo_head_big.png'), 60, 60, True)
            dialog.set_logo(pxbf)

            dialog.show_all()

        about_button.connect('clicked', show_dialog)

        # Start main handler
        headerbar_wdg = [box, None, about_button, refresh_button,
                         player_box, previous_b, stop_b, playpause_b, next_b,
                         None, win.get_object('box1'), self.main_window]
        self.wdg = [headerbar_wdg, win]

    def start_thread(self):
        # Tell extensions that Bluemindo is now launched
        self.extensions.load_event('OnBluemindoStarted', self.wdg)

        # Start the GTK main thread
        self.main_window.show()
        self.wdg[0][0].show_all()

        self.wdg[1].get_object('box3').show()
        self.wdg[1].get_object('box6').show()
        gtk_main()
