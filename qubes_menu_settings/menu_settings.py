# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2024 Marta Marczykowska-Górecka
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
Settings for Qubes App Menu.
"""

import os
import subprocess
import sys
from typing import List, Optional

import gi
import importlib.resources

import qubesadmin

from qubes_config.widgets.gtk_widgets import ImageListModeler

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from qubes_menu.constants import (
    INITIAL_PAGE_FEATURE,
    SORT_RUNNING_FEATURE,
    POSITION_FEATURE,
    DISABLE_RECENT_FEATURE,
)

MENU_PAGES = {
    "search_page": "Search",
    "app_page": "Applications",
    "favorites_page": "Favorites",
}

MENU_PAGES_DICT = {
    "Search": {"icon": "qappmenu-search", "object": "search_page"},
    "Applications": {"icon": "qappmenu-qube", "object": "app_page"},
    "Favorites": {"icon": "qappmenu-favorites", "object": "favorites_page"},
}

MENU_POSITIONS = {
    "top-left": "Top Left",
    "top-right": "Top Right",
    "bottom-left": "Bottom Left",
    "bottom-right": "Bottom Right",
    "mouse": "Mouse",
}

MENU_POSITIONS_DICT = {
    "Top Left": {"icon": "qappmenu-top-left", "object": "top-left"},
    "Top Right": {"icon": "qappmenu-top-right", "object": "top-right"},
    "Bottom Left": {"icon": "qappmenu-bottom-left", "object": "bottom-left"},
    "Bottom Right": {"icon": "qappmenu-bottom-right", "object": "bottom-right"},
    "Mouse": {"icon": "input-mouse-symbolic", "object": "mouse"},
}


SHORTCUTS_CHANNEL = "xfce4-keyboard-shortcuts"


def get_menu_shortcuts() -> Optional[List[str]]:
    """
    Get the Xfce keyboard shortcuts that open the menu, as labels like
    "Super+M". Returns None if not running Xfce.
    """
    if "XFCE" not in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
        return None
    try:
        output = subprocess.run(
            ["xfconf-query", "-c", SHORTCUTS_CHANNEL, "-l", "-v"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None

    properties = {}
    for line in output.splitlines():
        path, _, value = line.partition(" ")
        properties[path] = value.strip()

    # Xfce uses either the default list or the user's own (custom) list
    if properties.get("/commands/custom/override") == "true":
        prefix = "/commands/custom/"
    else:
        prefix = "/commands/default/"

    shortcuts = []
    for path, command in properties.items():
        if not path.startswith(prefix):
            continue
        accelerator = path[len(prefix) :]
        if "/" in accelerator or accelerator == "override":
            continue
        if not (
            command.split(" ", 1)[0].endswith("qubes-app-menu")
            or "org.qubesos.appmenu" in command
        ):
            continue
        key, mods = Gtk.accelerator_parse(accelerator)
        if key:
            shortcuts.append(Gtk.accelerator_get_label(key, mods))
    return sorted(shortcuts)


class AppMenuSettings(Gtk.Application):
    """
    Qubes Menu Settings app.
    """

    def __init__(self, qapp: qubesadmin.Qubes):
        """
        :param qapp: qubesadmin.Qubes object
        """
        super().__init__(application_id="org.qubesos.appmenusettings")
        self.qapp = qapp
        self.vm = self.qapp.domains[self.qapp.local_name]

    def do_activate(self, *args, **kwargs):
        """
        Method called whenever this program is run; it executes actual setup
        only at true first start, in other cases just presenting the main window
        to user.
        """
        self.perform_setup()
        assert self.main_window
        self.main_window.show()
        self.hold()

    def perform_setup(self):
        # pylint: disable=attribute-defined-outside-init
        """
        The function that performs actual widget realization and setup.
        """
        self.builder = Gtk.Builder()

        glade_path = (
            importlib.resources.files("qubes_menu_settings")
            / "menu_settings.glade"
        )
        with importlib.resources.as_file(glade_path) as path:
            self.builder.add_from_file(str(path))

        self.main_window: Gtk.ApplicationWindow = self.builder.get_object(
            "main_window"
        )

        self.confirm_button: Gtk.Button = self.builder.get_object(
            "button_confirm"
        )
        self.apply_button: Gtk.Button = self.builder.get_object("button_apply")
        self.cancel_button: Gtk.Button = self.builder.get_object(
            "button_cancel"
        )

        self.starting_page_combo: Gtk.ComboBox = self.builder.get_object(
            "starting_page_combo"
        )

        self.menu_position_combo: Gtk.ComboBox = self.builder.get_object(
            "menu_position_combo"
        )

        self.sort_running_check: Gtk.CheckButton = self.builder.get_object(
            "sort_running_to_top_check"
        )

        self.show_recent_check: Gtk.CheckButton = self.builder.get_object(
            "show_recent_apps_check"
        )
        self.shortcut_box: Gtk.Box = self.builder.get_object("shortcut_box")
        self.shortcut_label: Gtk.Label = self.builder.get_object(
            "shortcut_label"
        )
        self.keyboard_settings_button: Gtk.Button = self.builder.get_object(
            "keyboard_settings_button"
        )
        self.keyboard_settings_button.connect(
            "clicked", self._open_keyboard_settings
        )

        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()

        css_path = (
            importlib.resources.files("qubes_menu_settings")
            / "menu_settings.css"
        )
        with importlib.resources.as_file(css_path) as path:
            provider.load_from_path(str(path))

        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.confirm_button.connect("clicked", self._save_exit)
        self.apply_button.connect("clicked", self._save)
        self.cancel_button.connect("clicked", self._quit)

        self.initial_page_model = ImageListModeler(
            self.starting_page_combo, MENU_PAGES_DICT
        )

        self.menu_position_model = ImageListModeler(
            self.menu_position_combo, MENU_POSITIONS_DICT
        )

        self.load_state()

    def load_state(self):
        """
        Load current settings from local vm's features.
        """
        initial_page = self.vm.features.get(INITIAL_PAGE_FEATURE, "app_page")
        if initial_page not in MENU_PAGES:
            initial_page = "app_page"

        self.initial_page_model.select_name(MENU_PAGES[initial_page])
        self.initial_page_model.update_initial()

        menu_position = self.vm.features.get(POSITION_FEATURE, "mouse")
        if menu_position not in MENU_POSITIONS:
            menu_position = "mouse"

        self.menu_position_model.select_name(MENU_POSITIONS[menu_position])
        self.menu_position_model.update_initial()

        sort_running = bool(self.vm.features.get(SORT_RUNNING_FEATURE, False))
        self.sort_running_check.set_active(sort_running)

        disable_recent = bool(
            self.vm.features.get(DISABLE_RECENT_FEATURE, False)
        )
        self.show_recent_check.set_active(not disable_recent)

        self.load_shortcuts()

    def load_shortcuts(self):
        """
        Show the keyboard shortcuts that open the menu, and where to change
        them. Only on Xfce, where they can be read.
        """
        shortcuts = get_menu_shortcuts()
        if shortcuts is None:
            self.shortcut_box.hide()
            return
        if shortcuts:
            names = ", ".join(
                f"<b>{GLib.markup_escape_text(s)}</b>" for s in shortcuts
            )
            text = (
                f"Keyboard shortcut to open the menu: {names}. To change it, "
                "go to Keyboard settings → Application Shortcuts."
            )
        else:
            text = (
                "No keyboard shortcut opens the menu. To add one, go to "
                "Keyboard settings → Application Shortcuts and use the "
                "command <tt>qubes-app-menu</tt>."
            )
        self.shortcut_label.set_markup(text)
        self.shortcut_box.set_no_show_all(False)
        self.shortcut_box.show_all()

    def _open_keyboard_settings(self, *_args):
        # pylint: disable=consider-using-with
        subprocess.Popen(["xfce4-keyboard-settings"])

    def _quit(self, *_args):
        self.quit()

    def _save(self, *_args):
        """Save changes."""
        old_sort_running = self.vm.features.get(SORT_RUNNING_FEATURE, None)

        if self.sort_running_check.get_active():
            if not old_sort_running:
                self.vm.features[SORT_RUNNING_FEATURE] = "1"
        else:
            if old_sort_running:
                del self.vm.features[SORT_RUNNING_FEATURE]

        old_disable_recent = self.vm.features.get(DISABLE_RECENT_FEATURE, None)

        if self.show_recent_check.get_active():
            if old_disable_recent:
                del self.vm.features[DISABLE_RECENT_FEATURE]
        else:
            if not old_sort_running:
                self.vm.features[DISABLE_RECENT_FEATURE] = "1"

        old_initial_page = self.vm.features.get(
            INITIAL_PAGE_FEATURE, "app_page"
        )

        if self.initial_page_model.get_selected() != old_initial_page:
            self.vm.features[INITIAL_PAGE_FEATURE] = (
                self.initial_page_model.get_selected()
            )

        old_menu_position = self.vm.features.get(POSITION_FEATURE, "mouse")

        if self.menu_position_model.get_selected() != old_menu_position:
            self.vm.features[POSITION_FEATURE] = (
                self.menu_position_model.get_selected()
            )

    def _save_exit(self, *_args):
        self._save()
        self._quit()


def main():
    """
    Start the app
    """
    qapp = qubesadmin.Qubes()
    app = AppMenuSettings(qapp)
    app.run()


if __name__ == "__main__":
    sys.exit(main())
