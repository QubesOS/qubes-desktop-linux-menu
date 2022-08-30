# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2021 Marta Marczykowska-Górecka
#                               <marmarta@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.
"""
Miscellaneous Qubes Menu utility functions.
"""
import gi
import logging
import pkg_resources

from qubes_menu import constants
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib

import configparser

logger = logging.getLogger('qubes-appmenu')

def load_icon(icon_name, size: Gtk.IconSize = Gtk.IconSize.LARGE_TOOLBAR):
    """Load icon from provided name, if available. If not, attempt to treat
    provided name as a path. If icon not found in any of the above ways,
    load a blank icon of specified size.
    Returns GdkPixbuf.Pixbuf
    """
    _, width, height = Gtk.icon_size_lookup(size)
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, width, height)
    except (GLib.Error, TypeError):
        try:
            # icon name is a path
            image: GdkPixbuf.Pixbuf = Gtk.IconTheme.get_default().load_icon(
                icon_name, width, 0)
            return image
        except (TypeError, GLib.Error):
            # icon not found in any way
            pixbuf: GdkPixbuf.Pixbuf = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, True, 8, width, height)
            pixbuf.fill(0x000)
            return pixbuf


def show_error(title, text):
    """
    Helper function to display error messages.
    """
    dialog = Gtk.MessageDialog(
        None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK)
    dialog.set_title(title)
    dialog.set_markup(text)
    dialog.connect("response", lambda *x: dialog.destroy())
    dialog.show()

def read_settings(key):
    config = configparser.ConfigParser()
    try:
        config.read(constants.SETTINGS_PATH)
        return config[constants.SETTINGS][key]
    except:
        logger.info('Failed to open the settings file')
        

def write_settings(key, value):
    config = configparser.ConfigParser()
    try: 
        config.read(constants.SETTINGS_PATH)
    except:
        logger.info('Failed to open the settings file')
        return

    config.set(constants.SETTINGS, key, value)

    with open(constants.SETTINGS_PATH, 'w') as file:
        config.write(file)
