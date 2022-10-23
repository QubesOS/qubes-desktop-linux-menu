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
from typing import List

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib


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


def text_search(search_word: str, text_words: List[str]):
    """Text-searching function.
    Returns a match rank, if greater than 0, the searched phrase was found.
    The higher the number, the better the match.
    """
    if not search_word:
        return 0

    for text_word in text_words:
        if text_word.startswith(search_word):
            return 1
        if search_word in text_word:
            return 0.5
    return 0
