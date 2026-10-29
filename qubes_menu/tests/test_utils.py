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
import os
import time

from ..utils import highlight_words, run_detached

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def test_highlight_words():
    # make a mock highlight tag
    highlight_tag = "<span>"

    # create some labels
    label_1 = Gtk.Label(label="Come forth my lovely languorous Sphinx")
    label_2 = Gtk.Label(label="sphinx of black quartz, judge my vow")
    label_3 = Gtk.Label(label="A shape with lion body and the head of a man")

    labels = [label_1, label_2, label_3]

    highlight_words(labels, ["sphinx"], highlight_tag)

    assert (
        label_1.get_label()
        == "Come forth my lovely languorous <span>Sphinx</span>"
    )
    assert (
        label_2.get_label()
        == "<span>sphinx</span> of black quartz, judge my vow"
    )
    assert label_3.get_label() == "A shape with lion body and the head of a man"

    # further highlighting should not break things and should remove
    # old highlights

    highlight_words(labels, ["black"], highlight_tag)

    assert label_1.get_label() == "Come forth my lovely languorous Sphinx"
    assert (
        label_2.get_label()
        == "sphinx of <span>black</span> quartz, judge my vow"
    )
    assert label_3.get_label() == "A shape with lion body and the head of a man"

    # multiple words should work, even when they overlap

    highlight_words(labels, ["on", "lion", "languorous"], highlight_tag)

    assert (
        label_1.get_label()
        == "Come forth my lovely <span>languorous</span> Sphinx"
    )
    assert label_2.get_label() == "sphinx of black quartz, judge my vow"
    assert (
        label_3.get_label()
        == "A shape with <span>lion</span> body and the head of a man"
    )


def _wait_until(condition, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_run_detached_reaps_child():
    # The menu drops the handle while the child is still running. Once the
    # child exits it must not stay a zombie until the next launch, as it did
    # with a discarded Popen.
    proc = run_detached(["sleep", "0.5"])
    pid = int(proc.get_identifier())
    del proc
    assert _wait_until(lambda: not os.path.exists(f"/proc/{pid}"))


def test_run_detached_stdin_is_devnull():
    proc = run_detached(["sleep", "10"])
    try:
        pid = int(proc.get_identifier())
        assert os.readlink(f"/proc/{pid}/fd/0") == "/dev/null"
    finally:
        proc.force_exit()
