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
from xdg.DesktopEntry import DesktopEntry
from ..desktop_file_manager import ApplicationInfo, DesktopFileManager
from ..settings_page import SettingsPage
from qubesadmin.tests import TestVM
from unittest.mock import Mock
import asyncio

correct_bytes = b"""
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
"""

correct_bytes_2 = b"""
[Desktop Entry]
Version=1.0
Type=Application
Terminal=false
X-Qubes-VmName=template
Icon=/tmp/test.png
Name=template: XTerm
GenericName=template: Terminal
Comment=standard terminal emulator for the X window system
Categories=System;TerminalEmulator;X-Qubes-VM;
Exec=qvm-run -q -a --service -- template qubes.StartApp+xterm
X-Qubes-DispvmExec=qvm-run -q -a --service --dispvm=template -- qubes.StartApp+xterm
"""

correct_local_qubes = b"""
[Desktop Entry]
Type=Application
Exec=qubes-backup
Icon=qubes-manager
Terminal=false
Name=Backup Qubes
GenericName=Backup Qubes
StartupNotify=false
Categories=Settings;X-XFCE-SettingsDialog
"""

correct_local_non_qubes = b"""
[Desktop Entry]
Version=1.0
Name=Power Manager
GenericName=Power Manager
Comment=Settings for the Xfce Power Manager
Exec=xfce4-power-manager-settings
Icon=xfce4-power-manager-settings
Terminal=false
Type=Application
Categories=XFCE;GTK;Settings;DesktopSettings;X-XFCE-SettingsDialog;X-XFCE-HardwareSettings;
NotShowIn=GNOME;KDE;Unity;
StartupNotify=true
X-XfcePluggable=true
X-XfceHelpComponent=xfce4-power-manager
X-XfceHelpPage=start
"""

correct_other = b"""
[Desktop Entry]
Version=1.0
Name=Pinta
Comment=Easily create and edit images
GenericName=Image Editor
X-GNOME-FullName=Pinta Image Editor
TryExec=pinta
Exec=pinta %F
Icon=pinta
StartupNotify=false
StartupWMClass=Pinta
Terminal=false
Type=Application
Categories=Graphics;2DGraphics;RasterGraphics;GTK;
Keywords=draw;drawing;paint;painting;graphics;raster;2d;
MimeType=image/bmp;image/gif;image/jpeg;image/jpg;image/pjpeg;image/png;image/svg+xml;image/tiff;image/x-bmp;image/x-gray;image/x-icb;image/x-ico;image/x-png;image/x-portable-anymap;image/x-portable-bitmap;image/x-portable-graymap;image/x-portable-pixmap;image/x-xbitmap;image/x-xpixmap;image/x-pcx;image/x-targa;image/x-tga;image/openraster;
"""


def test_appinfo_correct_file(tmp_path, test_qapp):
    file_path = tmp_path / "test.desktop"
    file_path.write_bytes(correct_bytes)

    desktop_entry = DesktopEntry(file_path)

    app_info = ApplicationInfo(test_qapp, file_path)
    app_info.load_data(desktop_entry)

    assert app_info.app_name == "XTerm"
    assert str(app_info.vm) == str(TestVM("test-vm"))
    assert app_info.app_icon == "/tmp/test.png"
    assert app_info.vm_icon == "appvm-green"

    assert app_info.entry_name == "XTerm" or app_info.entry_name == "test.desktop"
    assert not app_info.disposable
    assert app_info.is_qubes_specific()

    assert app_info.get_command_for_vm(TestVM("test-vm")) == [
        "qvm-run",
        "-q",
        "-a",
        "--service",
        "--",
        "test-vm",
        "qubes.StartApp+xterm",
    ]

    assert app_info.get_command_for_vm(TestVM("other-vm")) == [
        "qvm-run",
        "-q",
        "-a",
        "--service",
        "--",
        "other-vm",
        "qubes.StartApp+xterm",
    ]


def test_file_dvmtemplate(tmp_path, test_qapp):
    correct_dvm_template = b"""
    [Desktop Entry]
    Version=1.0
    Type=Application
    Terminal=false
    X-Qubes-VmName=default-dvm
    Icon=/test/firefox.png
    Name=default-dvm: Firefox
    GenericName=template-dvm: Web Browser
    Comment=Browse the Web
    Categories=Network;WebBrowser;X-Qubes-VM;
    X-Qubes-NonDispvmExec=qvm-run -q -a --service -- default-dvm qubes.StartApp+firefox
    Exec=qvm-run -q -a --service --dispvm=default-dvm -- qubes.StartApp+firefox
    """

    file_path = tmp_path / "test.desktop"
    file_path.write_bytes(correct_dvm_template)

    desktop_entry = DesktopEntry(file_path)

    app_info = ApplicationInfo(test_qapp, file_path)
    app_info.load_data(desktop_entry)

    assert app_info.app_name == "Firefox"
    assert str(app_info.vm) == str(TestVM("default-dvm"))
    assert app_info.app_icon == "/test/firefox.png"
    assert app_info.vm_icon == "templatevm-green"
    assert app_info.disposable
    assert app_info.is_qubes_specific()
    assert app_info.get_command_for_vm("default-dvm") == [
        "qvm-run",
        "-q",
        "-a",
        "--service",
        "--dispvm=default-dvm",
        "--",
        "qubes.StartApp+firefox",
    ]


def test_appinfo_local(tmp_path, test_qapp):
    file_path_qubes = tmp_path / "test.desktop"
    file_path_non_qubes = tmp_path / "test2.desktop"
    file_path_qubes.write_bytes(correct_local_qubes)
    file_path_non_qubes.write_bytes(correct_local_non_qubes)

    desktop_entry_qubes = DesktopEntry(file_path_qubes)
    desktop_entry_non_qubes = DesktopEntry(file_path_non_qubes)

    app_info_qubes = ApplicationInfo(test_qapp, file_path_qubes)
    app_info_non_qubes = ApplicationInfo(test_qapp, file_path_non_qubes)
    app_info_qubes.load_data(desktop_entry_qubes)
    app_info_non_qubes.load_data(desktop_entry_non_qubes)

    assert app_info_qubes.app_name == "Backup Qubes"
    assert app_info_non_qubes.app_name == "Power Manager"
    assert app_info_qubes.vm is None
    assert app_info_non_qubes.vm is None
    assert app_info_qubes.vm_icon is None
    assert app_info_non_qubes.vm_icon is None

    assert app_info_qubes.app_icon == "qubes-manager"
    assert app_info_non_qubes.app_icon == "xfce4-power-manager-settings"

    assert not app_info_non_qubes.disposable
    assert not app_info_qubes.disposable
    assert not app_info_qubes.is_qubes_specific()
    assert not app_info_non_qubes.is_qubes_specific()

    assert app_info_qubes.get_command_for_vm(None) == ["qubes-backup"]
    assert app_info_non_qubes.get_command_for_vm(None) == [
        "xfce4-power-manager-settings"
    ]

    assert app_info_qubes.get_command_for_vm("dom0") == ["qubes-backup"]
    assert app_info_non_qubes.get_command_for_vm("dom0") == [
        "xfce4-power-manager-settings"
    ]


def test_file_qubes_virtual(tmp_path, test_qapp):
    qubes_virtual = b"""
[Desktop Entry]
Version=1.0
Type=Application
TryExec=qubes-vm-settings
Exec=qubes-vm-settings fedora-32
Icon=qubes-appmenu-select
Terminal=false
Name=fedora-32: Qube Settings
GenericName=fedora-32: Qube Settings
StartupNotify=false
Categories=System;X-Qubes-VM;"""

    file_path = tmp_path / "test.desktop"
    file_path.write_bytes(qubes_virtual)

    desktop_entry = DesktopEntry(file_path)

    app_info = ApplicationInfo(test_qapp, file_path)
    app_info.load_data(desktop_entry)

    assert not app_info.vm


def test_space_exec(tmp_path, test_qapp):
    qubes_virtual = b"""
[Desktop Entry]
Version=1.0
Type=Application
Exec=command "a vm"
Icon=qubes
Terminal=false
Name=Generic Name
GenericName=Generic Name
StartupNotify=false
Categories=System;X-Qubes-VM;"""

    file_path = tmp_path / "test.desktop"
    file_path.write_bytes(qubes_virtual)

    desktop_entry = DesktopEntry(file_path)

    app_info = ApplicationInfo(test_qapp, file_path)
    app_info.load_data(desktop_entry)

    assert app_info.get_command_for_vm(None) == ["command", "a vm"]


def test_special_characters_exec(tmp_path, test_qapp):
    qubes_virtual = b"""
[Desktop Entry]
Version=1.0
Type=Application
Exec=command "a\\b\\c"
Icon=qubes
Terminal=false
Name=Generic Name
GenericName=Generic Name
StartupNotify=false
Categories=System;X-Qubes-VM;"""

    file_path = tmp_path / "test.desktop"
    file_path.write_bytes(qubes_virtual)

    desktop_entry = DesktopEntry(file_path)

    app_info = ApplicationInfo(test_qapp, file_path)
    app_info.load_data(desktop_entry)

    assert app_info.get_command_for_vm(None) == ["command", "a\\b\\c"]


@pytest.mark.asyncio
async def test_file_manager(tmp_path, test_qapp):
    DesktopFileManager.desktop_dirs = [tmp_path]
    (tmp_path / "test.desktop").write_bytes(correct_bytes)
    (tmp_path / "wrong.desktop").write_bytes(b"faulty")

    dfm = DesktopFileManager(test_qapp)
    assert len(dfm.app_entries) == 1

    entry_list = []

    def add_entry(en):
        m = Mock()
        entry_list.append(m)
        en.entries.append(m)

    dfm.register_callback(add_entry)

    assert len(entry_list) == 1

    (tmp_path / "test2.desktop").write_bytes(correct_bytes_2)

    # process file events
    await asyncio.sleep(1)

    assert len(entry_list) == 2

    (tmp_path / "test.desktop").write_bytes(correct_bytes)
    (tmp_path / "test2.desktop").write_bytes(correct_bytes_2)
    (tmp_path / "wrong.desktop").write_bytes(b"faulty")

    # process file events
    await asyncio.sleep(1)

    assert len(entry_list) == 2

    for entry in entry_list:
        assert entry.update_contents.called


def test_filter_system(tmp_path, test_qapp):
    file_path_non_qubes = tmp_path / "correct_local_non.desktop"
    file_path_non_qubes.write_bytes(correct_local_non_qubes)
    desktop_entry_non_qubes = DesktopEntry(file_path_non_qubes)
    app_info_non_qubes = ApplicationInfo(test_qapp, file_path_non_qubes)
    app_info_non_qubes.load_data(desktop_entry_non_qubes)
    row_non_qubes = Mock()
    row_non_qubes.app_info = app_info_non_qubes

    file_path_qubes = tmp_path / "correct_local_qubes.desktop"
    file_path_qubes.write_bytes(correct_local_qubes)
    desktop_entry_qubes = DesktopEntry(file_path_qubes)
    app_info_qubes = ApplicationInfo(test_qapp, file_path_qubes)
    app_info_qubes.load_data(desktop_entry_qubes)
    row_qubes = Mock()
    row_qubes.app_info = app_info_qubes

    file_path_other = tmp_path / "correct_other.desktop"
    file_path_other.write_bytes(correct_other)
    desktop_entry_other = DesktopEntry(file_path_other)
    app_info_other = ApplicationInfo(test_qapp, file_path_other)
    app_info_other.load_data(desktop_entry_other)
    row_other = Mock()
    row_other.app_info = app_info_other

    assert not SettingsPage._filter_qubes_tools(row_non_qubes)
    assert SettingsPage._filter_system_settings(row_non_qubes)
    assert not SettingsPage._filter_other(row_non_qubes)

    assert SettingsPage._filter_qubes_tools(row_qubes)
    assert not SettingsPage._filter_system_settings(row_qubes)
    assert not SettingsPage._filter_other(row_qubes)

    assert not SettingsPage._filter_qubes_tools(row_other)
    assert not SettingsPage._filter_system_settings(row_other)
    assert SettingsPage._filter_other(row_other)
