# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2022 Marta Marczykowska-Górecka
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
"""Search page for App Menu"""
from typing import Dict, Optional, Set, Union

from .desktop_file_manager import DesktopFileManager
from .custom_widgets import SearchVMRow, AnyVMRow, ControlList, KeynavController
from .app_widgets import SearchAppEntry
from .vm_manager import VMEntry, VMManager
from .page_handler import MenuPage
from .utils import load_icon, parse_search

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class RecentSearchRow(Gtk.ListBoxRow):
    """
    Gtk.ListBoxRow with a recently searched text.
    """

    def __init__(self, search_text: str):
        super().__init__()
        self.search_text = search_text
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.recent_icon = Gtk.Image.new_from_pixbuf(load_icon("qappmenu-search"))
        self.hbox.pack_start(self.recent_icon, False, False, 5)
        self.search_label = Gtk.Label(label=search_text, xalign=0)
        self.hbox.pack_start(self.search_label, False, False, 5)
        self.get_style_context().add_class("app_entry")
        self.add(self.hbox)
        self.show_all()


class RecentSearchManager:
    """Class for managing the list of recent searches."""

    SEARCH_VALUES_TO_KEEP = 10

    def __init__(
        self, recent_list: Gtk.ListBox, search_box: Gtk.SearchEntry, enabled: bool
    ):
        self.recent_enabled = enabled
        self.recent_list_box = recent_list
        self.search_box = search_box
        self.recent_searches: Dict[str, RecentSearchRow] = {}
        self.recent_list_box.connect("row-activated", self._row_clicked)

    def set_recent_enabled(self, state):
        """Set whether recent searches should be stored or not."""
        self.recent_enabled = state
        self.recent_searches.clear()
        for child in self.recent_list_box.get_children():
            self.recent_list_box.remove(child)

        label = Gtk.Label()
        label.get_style_context().add_class("placeholder")
        label.set_visible(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.START)

        if state:
            label.set_text("No recent searches")
        else:
            label.set_text(
                "Recent searches saving disabled.\nUse Menu Settings to enable."
            )

        self.recent_list_box.set_placeholder(label)

    def add_new_recent_search(self, text: str):
        """Add new recent search entry"""
        if not self.recent_enabled:
            return
        if not text:
            return

        if text in self.recent_searches:
            old_row = self.recent_searches[text]
            # move to top of the list
            self.recent_list_box.remove(old_row)
            self.recent_list_box.insert(old_row, 0)
            return

        if len(self.recent_searches) == self.SEARCH_VALUES_TO_KEEP + 1:
            last_row: RecentSearchRow = self.recent_list_box.get_children()[-1]
            del self.recent_searches[last_row.search_text]
            self.recent_list_box.remove(last_row)

        row = RecentSearchRow(text)
        self.recent_list_box.insert(row, 0)
        self.recent_searches[text] = row

    def _row_clicked(self, _widget, row: RecentSearchRow):
        self.search_box.set_text(row.search_text)


class RecentAppsManager:
    """Class for managing recently run apps"""

    APPS_TO_KEEP = 10

    def __init__(
        self,
        recent_list: Gtk.ListBox,
        desktop_file_manager: DesktopFileManager,
        vm_manager: VMManager,
        enabled: bool,
    ):
        self.recent_enabled = enabled
        self.recent_list_box = recent_list
        self.desktop_file_manager = desktop_file_manager
        self.vm_manager = vm_manager
        self.recent_apps: list[SearchAppEntry] = []
        self.recent_list_box.connect("row-activated", self._row_clicked)
        self.recent_list_box.get_toplevel().get_application().connect(
            "app-started", self.add_new_recent_app
        )

    def set_recent_enabled(self, state):
        """Set whether recent apps  should be stored or not."""
        self.recent_enabled = state
        self.recent_apps.clear()
        for child in self.recent_list_box.get_children():
            self.recent_list_box.remove(child)

        label = Gtk.Label()
        label.get_style_context().add_class("placeholder")
        label.set_visible(True)
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.START)

        if state:
            label.set_text("No recent applications")
        else:
            label.set_text(
                "Recent application saving disabled.\nUse Menu Settings to enable."
            )

        self.recent_list_box.set_placeholder(label)

    def add_new_recent_app(self, _widget, app_path: str):
        """Add new "recent" record, based on .desktop file path given as string"""
        if not self.recent_enabled:
            return

        # only add if not exists, if exists: bump to top and return
        for app_entry in self.recent_apps:
            if app_entry.app_info.file_path.name == app_path:
                self.recent_list_box.remove(app_entry)
                self.recent_list_box.insert(app_entry, 0)
                return

        app_info = self.desktop_file_manager.get_app_info_by_name(app_path)
        if not app_info:
            return
        new_entry = SearchAppEntry(app_info, self.vm_manager)
        self.recent_apps.append(new_entry)
        self.recent_list_box.insert(new_entry, 0)

        if len(self.recent_apps) == self.APPS_TO_KEEP + 1:
            last_row: SearchAppEntry = self.recent_list_box.get_children()[-1]
            del self.recent_apps[last_row]
            self.recent_list_box.remove(last_row)

    @staticmethod
    def _row_clicked(_widget, row: SearchAppEntry):
        if hasattr(row, "app_info"):
            row.run_app(row.app_info.vm)


class SearchPage(MenuPage):
    """
    Helper class for managing the Search menu page.
    """

    def __init__(
        self,
        vm_manager: VMManager,
        builder: Gtk.Builder,
        desktop_file_manager: DesktopFileManager,
    ):
        """
        :param vm_manager: VM Manager object
        :param builder: Gtk.Builder with loaded glade object
        :param desktop_file_manager: Desktop File Manager object
        """
        self.vm_manager = vm_manager
        self.desktop_file_manager = desktop_file_manager

        self.page_widget: Gtk.Grid = builder.get_object("search_page")

        self.sort_running = False  # sort running vms to top
        self.recent_enabled = True

        self.vm_list: Gtk.ListBox = builder.get_object("search_vm_list")
        self.app_list: Gtk.ListBox = builder.get_object("search_app_list")
        self.search_entry: Gtk.SearchEntry = builder.get_object("search_entry")

        self.selected_vm_row: Optional[SearchVMRow] = None
        self.filtered_vms: Set[str] = set()

        self.main_notebook = builder.get_object("main_notebook")

        self.search_entry.connect("search-changed", self._do_search)
        self.search_entry.connect("key-press-event", self._search_key_press)

        desktop_file_manager.register_callback(self._app_info_callback)

        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect("row-activated", self._app_clicked)

        self.vm_list.add(AnyVMRow())
        vm_manager.register_new_vm_callback(self._vm_callback)
        self.vm_list.set_filter_func(self._is_vm_fitting)

        self.app_list.set_sort_func(self._sort_apps)
        self.vm_list.set_sort_func(self._sort_vms)
        self.app_list.invalidate_sort()
        self.vm_list.invalidate_sort()

        self.recent_list: Gtk.ListBox = builder.get_object("search_recent_list")
        self.recent_app_list: Gtk.ListBox = builder.get_object(
            "search_recent_apps_list"
        )

        self.app_view: Gtk.ScrolledWindow = builder.get_object("search_app_view")
        self.app_placeholder: Gtk.Label = builder.get_object("search_app_placeholder")
        self.vm_view: Gtk.ScrolledWindow = builder.get_object("search_vm_view")
        self.recent_box: Gtk.Box = builder.get_object("search_no_box")

        self.recent_search_manager = RecentSearchManager(
            self.recent_list, self.search_entry, self.recent_enabled
        )
        self.recent_apps_manager = RecentAppsManager(
            self.recent_app_list,
            self.desktop_file_manager,
            self.vm_manager,
            self.recent_enabled,
        )

        self.vm_list.connect("row-selected", self._selection_changed)
        self.search_entry.connect("activate", self._move_to_first)

        self.control_list = ControlList(self)
        self.page_widget.attach(self.control_list, 1, 4, 1, 1)
        self.control_list.connect("row-activated", self._app_clicked)
        self.control_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.keynav_manager = KeynavController(
            widgets_in_order=[self.app_list, self.control_list]
        )

    def _app_clicked(self, _widget, row):
        self.recent_search_manager.add_new_recent_search(self.search_entry.get_text())
        if self.selected_vm_row:
            row.run_app(self.selected_vm_row.vm_entry.vm)
        elif hasattr(row, "app_info"):
            row.run_app(row.app_info.vm)

    def _app_info_callback(self, app_info):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        entry = SearchAppEntry(app_info, self.vm_manager)
        self.app_list.add(entry)

    def _vm_callback(self, vm_entry: VMEntry):
        """
        Callback to be performed on all newly loaded VMEntry instances.
        """
        if vm_entry:
            vm_row = SearchVMRow(vm_entry)
            vm_row.show_all()
            vm_entry.entries.append(vm_row)
            self.vm_list.add(vm_row)
            self.vm_list.invalidate_filter()
            self.vm_list.invalidate_sort()

    def _do_search(self, *_args):
        has_search = bool(self.search_entry.get_text())
        self.app_view.set_visible(has_search)
        self.recent_box.set_visible(not has_search)

        self._filter_lists()

        self.vm_view.set_visible(has_search and not self.app_placeholder.get_mapped())

        if not self.app_placeholder.get_mapped():
            for row in self.app_list.get_children():
                if row.get_mapped():
                    self.app_list.select_row(row)
                    break

    def _search_key_press(self, _widget, event):
        """
        Tab on search should move focus to main notebook tabs
        if there are no search results available.
        Enter should activate the first search result.
        """
        if event.keyval == Gdk.KEY_Tab:
            if self.app_placeholder.get_mapped():
                self.main_notebook.grab_focus()
                return True
        if event.keyval == Gdk.KEY_Return:
            if self.app_placeholder.get_mapped():
                # this is needed because placeholder is technically a child
                # of the app_list
                return False
            for row in self.app_list.get_children():
                if row.get_mapped():
                    self.app_list.select_row(row)
                    row.activate()
                    return True
        return False

    def _move_to_first(self, *_args):
        """
        When Enter is pressed, we should move to first found row.
        """
        for row in self.app_list.get_children():
            if row.get_mapped():
                self.app_list.select_row(row)
                return

    def _sort_vms(self, vmentry: SearchVMRow, other_entry: SearchVMRow):
        if isinstance(vmentry, AnyVMRow):
            return -1
        if isinstance(other_entry, AnyVMRow):
            return 1
        if self.sort_running:
            if vmentry.vm_entry.power_state != other_entry.vm_entry.power_state:
                if vmentry.vm_entry.power_state == "Running":
                    return -1
                return 1
        return vmentry.sort_order > other_entry.sort_order

    def _sort_apps(self, appentry: SearchAppEntry, other_entry: SearchAppEntry):
        """
        # word is delineated by space and - and _
        Sorting algorithm prefers searched words being found at the start
        of a word.
        """
        search_words = parse_search(self.search_entry.get_text())
        result_1 = appentry.find_text(search_words)
        result_2 = other_entry.find_text(search_words)
        if result_1 > result_2:
            return -1
        if result_1 < result_2:
            return 1
        return 0

    def _is_app_fitting(self, appentry: SearchAppEntry):
        """Show only apps matching the current search text and, if
        qube is selected, matching a selected qube."""
        if self.selected_vm_row:
            if appentry.vm_name != self.selected_vm_row.vm_name:
                return False

        search_words = parse_search(self.search_entry.get_text())
        found_result = appentry.find_text(search_words)
        return found_result > 0

    def _is_vm_fitting(self, vmrow: Union[SearchVMRow, AnyVMRow]):
        """Show all vms where a matching app was found, and show
        the Any Qube option if any app was found."""
        if vmrow.vm_name:
            return vmrow.vm_name in self.filtered_vms
        return bool(self.filtered_vms)

    def _filter_lists(self):
        # selection of the All Qubes row is necessary to get all
        # possible qubes by filtering apps; if this behavior should be
        # changed (to e.g. not deselect qube when typing), this must be
        # refactored
        self.vm_list.select_row(self.vm_list.get_row_at_index(0))

        self.filtered_vms.clear()

        self.app_list.invalidate_filter()
        self.app_list.invalidate_sort()

        for child in self.app_list.get_children():
            if child.get_mapped():
                self.filtered_vms.add(child.vm_name)

        self.vm_list.invalidate_filter()
        self.vm_list.invalidate_sort()

    def initialize_page(self):
        """
        Initialize own state.
        """
        self.search_entry.set_text("")
        self.app_list.select_row(None)
        self.vm_list.select_row(None)
        self.app_view.set_visible(False)
        self.vm_view.set_visible(False)
        self.recent_box.set_visible(True)

        self._filter_lists()

        self.search_entry.grab_focus_without_selecting()

    def enable_recent(self, state: bool):
        """Enable/disable storing recent apps/searches"""
        self.recent_enabled = state
        self.recent_search_manager.set_recent_enabled(state)
        self.recent_apps_manager.set_recent_enabled(state)

        app_label = Gtk.Label()
        app_label.get_style_context().add_class("placeholder")
        search_label = Gtk.Label()
        search_label.get_style_context().add_class("placeholder")
        app_label.set_visible(True)
        search_label.set_visible(True)

        if state:
            app_label.set_text("No recent applications")
            search_label.set_text("No recent searches")
        else:
            app_label.set_text(
                "Recent application saving disabled.\nUse Menu Settings to enable."
            )
            search_label.set_text(
                "Recent searches saving disabled.\nUse Menu Settings to enable."
            )

        self.recent_app_list.set_placeholder(app_label)
        self.recent_list.set_placeholder(search_label)

    def reset_page(self):
        """Reset page after hiding the menu."""
        self.initialize_page()

    def _selection_changed(self, _widget, row: Optional[SearchVMRow]):
        if row is None or not row.vm_name:
            self.selected_vm_row = None
            self.control_list.hide()
        else:
            self.selected_vm_row = row
            self.control_list.show()
            self.control_list.update_visibility(row.vm_entry.power_state)
            self.control_list.unselect_all()
        self.app_list.invalidate_filter()
        self.app_list.select_row(None)

    def set_sorting_order(self, sort_running: bool = False):
        self.sort_running = sort_running
        self.vm_list.invalidate_sort()

    def get_selected_vm(self):
        """Get currently selected vm"""
        if self.selected_vm_row:
            return self.selected_vm_row.vm_entry
        return None
