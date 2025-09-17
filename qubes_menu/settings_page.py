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
Qubes App Menu settings/system tools page and related widgets.
"""
import qubesadmin.events

from .desktop_file_manager import DesktopFileManager
from . import custom_widgets
from .app_widgets import AppEntry, BaseAppEntry
from .page_handler import MenuPage

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class SettingsCategoryRow(custom_widgets.HoverListBox):
    """
    A custom widget representing a category of Settings; selects itself
    on hover.
    """

    def __init__(self, name, filter_func):
        super().__init__()
        self.name = name
        self.label = custom_widgets.LimitedWidthLabel(self.name)
        self.main_box.add(self.label)
        self.filter_func = filter_func
        self.get_style_context().add_class("settings_category_row")
        self.show_all()


class SettingsPage(MenuPage):
    """
    Helper class for managing the entirety of Settings menu page.
    """

    def __init__(
        self,
        qapp,
        builder: Gtk.Builder,
        desktop_file_manager: DesktopFileManager,
        dispatcher: qubesadmin.events.EventsDispatcher,
    ):
        self.qapp = qapp
        self.desktop_file_manager = desktop_file_manager
        self.dispatcher = dispatcher

        self.page_widget: Gtk.Box = builder.get_object("settings_page")

        self.app_list: Gtk.ListBox = builder.get_object("sys_tools_list")
        self.app_list.connect("row-activated", self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.sort_name > y.app_info.sort_name
        )
        self.app_list.set_filter_func(self._filter_apps)

        self.category_list: Gtk.ListBox = builder.get_object("settings_categories")

        self.category_list.connect("row-selected", self._category_clicked)
        self.category_list.add(
            SettingsCategoryRow("Qubes Tools", self._filter_qubes_tools)
        )
        self.category_list.add(
            SettingsCategoryRow("System Settings", self._filter_system_settings)
        )
        self.category_list.add(SettingsCategoryRow("Other", self._filter_other))

        self.desktop_file_manager.register_callback(self._app_info_callback)

        self.app_list.show_all()
        self.app_list.invalidate_filter()
        self.app_list.invalidate_sort()

    def initialize_page(self):
        """On initialization, no category should be selected."""
        self.category_list.select_row(None)

    def _filter_apps(self, row):
        filter_func = getattr(
            self.category_list.get_selected_row(), "filter_func", None
        )
        if not filter_func:
            return False
        return filter_func(row)

    @staticmethod
    def _filter_qubes_tools(row):
        if "X-XFCE-SettingsDialog" not in row.app_info.categories:
            return False
        return "qubes" in row.app_info.entry_name

    @staticmethod
    def _filter_system_settings(row):
        if "X-XFCE-SettingsDialog" in row.app_info.categories:
            return "qubes" not in row.app_info.entry_name
        if "Settings" in row.app_info.categories:
            return True
        return False

    @staticmethod
    def _filter_other(row):
        return not SettingsPage._filter_qubes_tools(
            row
        ) and not SettingsPage._filter_system_settings(row)

    def _category_clicked(self, *_args):
        self.app_list.invalidate_filter()

    @staticmethod
    def _app_clicked(_widget, row: AppEntry):
        row.run_app(None)

    def _app_info_callback(self, app_info):
        """
        Callback to be executed on every newly loaded ApplciationInfo object.
        """
        if not app_info.vm and not app_info.is_qubes_specific():
            entry = BaseAppEntry(app_info)
            self.app_list.add(entry)
