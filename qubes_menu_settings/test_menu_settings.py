# pylint: skip-file
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
import subprocess
from unittest import mock

from .menu_settings import AppMenuSettings, get_menu_shortcuts
from qubesadmin.tests.mock_app import MockQubesComplete


def test_menu_settings_load():
    qapp = MockQubesComplete()
    qapp._qubes["dom0"].features["menu-initial-page"] = "favorites_page"
    qapp._qubes["dom0"].features["menu-sort-running"] = "1"
    qapp._qubes["dom0"].features["menu-favorites"] = ""
    qapp._qubes["dom0"].features["menu-position"] = ""
    qapp._qubes["dom0"].features["menu-disable-recent"] = "1"

    qapp.update_vm_calls()

    app = AppMenuSettings(qapp)

    app.perform_setup()

    assert app.initial_page_model.get_selected() == "favorites_page"
    assert app.menu_position_model.get_selected() == "mouse"
    assert app.sort_running_check.get_active()
    assert not app.show_recent_check.get_active()


def test_menu_settings_change():
    qapp = MockQubesComplete()
    qapp._qubes["dom0"].features["menu-initial-page"] = "app_page"
    qapp._qubes["dom0"].features["menu-sort-running"] = ""
    qapp._qubes["dom0"].features["menu-favorites"] = ""
    qapp._qubes["dom0"].features["menu-position"] = "mouse"
    qapp._qubes["dom0"].features["menu-disable-recent"] = "1"

    qapp.update_vm_calls()

    app = AppMenuSettings(qapp)

    app.perform_setup()

    assert app.initial_page_model.get_selected() == "app_page"
    assert app.menu_position_model.get_selected() == "mouse"
    assert not app.sort_running_check.get_active()
    assert not app.show_recent_check.get_active()

    app.starting_page_combo.set_active_id(
        "Search"
    )  # the first option is search
    app.menu_position_combo.set_active_id(
        "Top Left"
    )  # the first option is Top Left
    app.sort_running_check.set_active(True)
    app.show_recent_check.set_active(True)

    qapp.expected_calls[
        ("dom0", "admin.vm.feature.Set", "menu-sort-running", b"1")
    ] = b"0\0"
    qapp.expected_calls[
        ("dom0", "admin.vm.feature.Set", "menu-initial-page", b"search_page")
    ] = b"0\0"
    qapp.expected_calls[
        ("dom0", "admin.vm.feature.Set", "menu-position", b"top-left")
    ] = b"0\0"
    qapp.expected_calls[
        ("dom0", "admin.vm.feature.Remove", "menu-disable-recent", None)
    ] = b"0\0"

    app._save()


def test_menu_settings_change2():
    qapp = MockQubesComplete()
    qapp._qubes["dom0"].features["menu-initial-page"] = "app_page"
    qapp._qubes["dom0"].features["menu-sort-running"] = ""
    qapp._qubes["dom0"].features["menu-favorites"] = ""
    qapp._qubes["dom0"].features["menu-position"] = "mouse"
    qapp._qubes["dom0"].features["menu-disable-recent"] = ""

    qapp.update_vm_calls()

    app = AppMenuSettings(qapp)

    app.perform_setup()

    assert app.initial_page_model.get_selected() == "app_page"
    assert not app.sort_running_check.get_active()
    assert app.show_recent_check.get_active()

    app.starting_page_combo.set_active_id("Favorites")
    app.show_recent_check.set_active(False)

    qapp.expected_calls[
        ("dom0", "admin.vm.feature.Set", "menu-initial-page", b"favorites_page")
    ] = b"0\0"
    qapp.expected_calls[
        ("dom0", "admin.vm.feature.Set", "menu-disable-recent", b"1")
    ] = b"0\0"

    app._save()


XFCONF_DEFAULT = """\
/commands/default/<Alt>F1                xfce4-popup-applicationsmenu
/commands/default/<Alt>F2                xfce4-appfinder --collapsed
/commands/default/<Alt>F2/startup-notify true
/commands/default/<Super>m               qubes-app-menu
/xfwm4/default/<Super>Tab                switch_window_key
"""

XFCONF_CUSTOM = XFCONF_DEFAULT + """\
/commands/custom/<Alt>F1                 xfce4-popup-applicationsmenu
/commands/custom/<Primary><Alt>space     qubes-app-menu --page 1
/commands/custom/<Super>a                gdbus call --session --dest \
org.qubesos.appmenu --object-path "/org/qubesos/appmenu" --method \
org.freedesktop.Application.Activate "{}"
/commands/custom/override                true
"""


def _xfconf(output):
    return mock.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, stdout=output),
    )


@mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "XFCE"})
def test_menu_shortcuts_default():
    with _xfconf(XFCONF_DEFAULT):
        assert get_menu_shortcuts() == ["Super+M"]


@mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "XFCE"})
def test_menu_shortcuts_custom():
    with _xfconf(XFCONF_CUSTOM):
        assert get_menu_shortcuts() == ["Ctrl+Alt+Space", "Super+A"]


@mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "XFCE"})
def test_menu_shortcuts_none():
    with _xfconf("/commands/default/<Alt>F1 xfce4-popup-applicationsmenu\n"):
        assert get_menu_shortcuts() == []


@mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "XFCE"})
def test_menu_shortcuts_no_xfconf():
    with mock.patch("subprocess.run", side_effect=FileNotFoundError):
        assert get_menu_shortcuts() is None


@mock.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "KDE"})
def test_menu_shortcuts_not_xfce():
    with mock.patch("subprocess.run") as run:
        assert get_menu_shortcuts() is None
        run.assert_not_called()


def test_menu_settings_shortcut_label():
    qapp = MockQubesComplete()
    for feature in (
        "menu-initial-page",
        "menu-sort-running",
        "menu-position",
        "menu-disable-recent",
    ):
        qapp._qubes["dom0"].features[feature] = ""
    qapp.update_vm_calls()
    app = AppMenuSettings(qapp)

    with mock.patch(
        "qubes_menu_settings.menu_settings.get_menu_shortcuts",
        return_value=["Super+M"],
    ):
        app.perform_setup()
    assert app.shortcut_box.get_visible()
    assert "Super+M" in app.shortcut_label.get_text()

    with mock.patch(
        "qubes_menu_settings.menu_settings.get_menu_shortcuts",
        return_value=None,
    ):
        app.load_shortcuts()
    assert not app.shortcut_box.get_visible()
