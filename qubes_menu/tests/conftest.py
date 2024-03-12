# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2020 Marta Marczykowska-Górecka
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

import pytest
import pkg_resources
from qubesadmin.tests.mock_app import MockQubesComplete


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


@pytest.fixture
def test_qapp():
    return MockQubesComplete()


@pytest.fixture
def test_builder():
    """Gtk builder with correct menu glade file"""
    builder = Gtk.Builder()
    builder.add_from_file(pkg_resources.resource_filename(
        'qubes_menu', 'qubes-menu.glade'))
    return builder


@pytest.fixture
def test_desktop_file_path(tmp_path):
    app_entry1 = b'''
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    X-Qubes-VmName=test-vm
    Icon=/tmp/test.png
    Name=test-vm: XTerm
    GenericName=test-vm: Terminal
    Comment=standard terminal emulator for the X window system
    Categories=System;TerminalEmulator;X-Qubes-VM;
    Exec=qvm-run -q -a --service -- test-vm qubes.StartApp+xterm
    X-Qubes-DispvmExec=qvm-run -q -a --service --dispvm=test-vm -- qubes.StartApp+xterm
    '''

    app_entry2 = b'''
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    X-Qubes-VmName=test-red
    Icon=/tmp/test.png
    Name=test-red: Firefox
    GenericName=test-red: Firefox
    Comment=Firefox web browser
    Keywords=big;blue;dragons
    Categories=System;X-Qubes-VM;
    Exec=qvm-run -q -a --service -- test-red qubes.StartApp+firefox
    X-Qubes-DispvmExec=qvm-run -q -a --service --dispvm=test-red -- qubes.StartApp+firefox
    '''

    app_entry3 = b'''
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    Icon=/tmp/test.png
    Name=Xfce Appearance Settings
    Comment=appearance settings for Xfce Desktop Environment
    Keywords=settings;desktop
    Categories=Gtk;Settings;X-XFCE-SettingsDialog;X-XFCE;
    Exec=xfce4-appearance-settings
    '''

    (tmp_path / 'test1.desktop').write_bytes(app_entry1)
    (tmp_path / 'test2.desktop').write_bytes(app_entry2)
    (tmp_path / 'test3.desktop').write_bytes(app_entry3)

    return tmp_path
