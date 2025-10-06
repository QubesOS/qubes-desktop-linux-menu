# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2023 Marta Marczykowska-Górecka
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
from ..utils import highlight_words

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def test_highlight_words():
    # make a mock highlight tag
    highlight_tag = "<span>"

    # create some labels
    label_1 = Gtk.Label("Come forth my lovely languorous Sphinx")
    label_2 = Gtk.Label("sphinx of black quartz, judge my vow")
    label_3 = Gtk.Label("A shape with lion body and the head of a man")

    labels = [label_1, label_2, label_3]

    highlight_words(labels, ["sphinx"], highlight_tag)

    assert label_1.get_label() == "Come forth my lovely languorous <span>Sphinx</span>"
    assert label_2.get_label() == "<span>sphinx</span> of black quartz, judge my vow"
    assert label_3.get_label() == "A shape with lion body and the head of a man"

    # further highlighting should not break things and should remove
    # old highlights

    highlight_words(labels, ["black"], highlight_tag)

    assert label_1.get_label() == "Come forth my lovely languorous Sphinx"
    assert label_2.get_label() == "sphinx of <span>black</span> quartz, judge my vow"
    assert label_3.get_label() == "A shape with lion body and the head of a man"

    # multiple words should work, even when they overlap

    highlight_words(labels, ["on", "lion", "languorous"], highlight_tag)

    assert label_1.get_label() == "Come forth my lovely <span>languorous</span> Sphinx"
    assert label_2.get_label() == "sphinx of black quartz, judge my vow"
    assert (
        label_3.get_label()
        == "A shape with <span>lion</span> body and the head of a man"
    )
