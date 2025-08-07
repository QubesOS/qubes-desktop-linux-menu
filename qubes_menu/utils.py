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
from typing import List, Optional

import gi

import qubesadmin.vm

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib


def load_icon(
    icon_name,
    size: Optional[Gtk.IconSize] = Gtk.IconSize.LARGE_TOOLBAR,
    pixel_size: Optional[int] = None,
):
    """Load icon from provided name, if available. If not, attempt to treat
    provided name as a path. If icon not found in any of the above ways,
    load a blank icon of specified size.
    Returns GdkPixbuf.Pixbuf
    """
    if size:
        _, width, height = Gtk.icon_size_lookup(size)
    else:
        width = pixel_size
        height = pixel_size
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, width, height)
    except (GLib.Error, TypeError):
        try:
            # icon name is a path
            image: GdkPixbuf.Pixbuf = Gtk.IconTheme.get_default().load_icon(
                icon_name, width, Gtk.IconLookupFlags.FORCE_SIZE
            )
            return image
        except (TypeError, GLib.Error):
            # icon not found in any way
            pixbuf: GdkPixbuf.Pixbuf = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, True, 8, width, height
            )
            pixbuf.fill(0x000)
            return pixbuf


def show_error(title, text):
    """
    Helper function to display error messages.
    """
    dialog = Gtk.MessageDialog(None, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK)
    dialog.set_title(title)
    dialog.set_markup(GLib.markup_escape_text(text))
    dialog.connect("response", lambda *x: dialog.destroy())
    dialog.show()


def parse_search(search_text: str) -> List[str]:
    """Parse search text into separate words"""
    search_words = search_text.lower().replace("-", " ").replace("_", " ").split(" ")
    return [w for w in search_words if w]


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


def highlight_words(
    labels: List[Gtk.Label], search_words: List[str], hl_tag: Optional[str] = None
) -> None:
    """Highlight provided search_words in the provided labels."""
    if not labels:
        return

    if not hl_tag:
        # try to find Application, if impossible, just give up on highlighting
        # because it means we are trying to highlight in the middle of
        # deleting some rows

        try:
            window = labels[0].get_ancestor(Gtk.Window)
            hl_tag = window.get_application().highlight_tag
        except AttributeError:
            return

    for label in labels:
        text = label.get_text()
        # remove existing highlighting
        label.set_markup(GLib.markup_escape_text(text))
        search_text = text.lower()
        found_intervals = []
        for word in search_words:
            start = search_text.find(word)
            if start >= 0:
                found_intervals.append((start, start + len(word)))

        if not found_intervals:
            continue

        found_intervals.sort(key=lambda x: x[0])
        result_intervals = [found_intervals[0]]
        for interval in found_intervals[1:]:
            if interval[0] <= result_intervals[-1][1]:
                result_intervals[-1] = (
                    result_intervals[-1][0],
                    max(result_intervals[-1][1], interval[1]),
                )
            else:
                result_intervals.append(interval)

        markup_list = []
        last_start = 0
        for start, end in result_intervals:
            markup_list.append(GLib.markup_escape_text(text[last_start:start]))
            markup_list.append(hl_tag)
            markup_list.append(GLib.markup_escape_text(text[start:end]))
            markup_list.append("</span>")
            last_start = end
        markup_list.append(GLib.markup_escape_text(text[last_start:]))

        label.set_markup("".join(markup_list))


def get_visible_child(widget: Gtk.Container, reverse=False):
    """
    Get a first (or last, if reverse=True) visible child of provided Container.
    """
    iterator = widget.get_children()
    if reverse:
        iterator = reversed(iterator)
    for child in iterator:
        if child.get_mapped() and child.get_sensitive():
            return child
    return None


def add_to_feature(vm: qubesadmin.vm.QubesVM, feature_name: str, text: str):
    """
    Add a given string to a feature containing a list of space-separated
    strings.
    """
    current_feature = vm.features.get(feature_name)
    if current_feature:
        feature_list = current_feature.split(" ")
    else:
        feature_list = []

    if text in feature_list:
        return
    feature_list.append(text)
    vm.features[feature_name] = " ".join(feature_list)


def remove_from_feature(vm: qubesadmin.vm.QubesVM, feature_name: str, text: str):
    """
    Remove a given string to a feature containing a list of space-separated
     strings.Can raise ValueError if ext was not found in the feature.
    """
    current_feature = vm.features.get(feature_name, "").split(" ")

    current_feature.remove(text)

    vm.features[feature_name] = " ".join(current_feature)
