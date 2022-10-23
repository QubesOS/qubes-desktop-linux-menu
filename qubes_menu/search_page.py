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
from typing import List, Set, Dict

from .desktop_file_manager import DesktopFileManager
from .custom_widgets import SearchVMRow
from .app_widgets import AppEntry, AppEntryWithVM
from .vm_manager import VMEntry, VMManager
from .page_handler import MenuPage
from .utils import load_icon

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class RecentSearchRow(Gtk.ListBoxRow):
    """
    Gtk.ListBoxRow with a recently searched text.
    """
    def __init__(self, search_text: str):
        super().__init__()
        self.search_text = search_text
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        # TODO: replace this icon with actual icon of a clock or smth?
        self.recent_icon = Gtk.Image.new_from_pixbuf(
            load_icon('qappmenu-search'))
        self.hbox.pack_start(self.recent_icon, False, False, 5)
        self.search_label = Gtk.Label(label=search_text, xalign=0)
        self.hbox.pack_start(self.search_label, False, False, 5)
        self.get_style_context().add_class('app_entry')
        self.add(self.hbox)
        self.show_all()


class RecentSearchManager:
    SEARCH_VALUES_TO_KEEP = 10
    def __init__(self, recent_list: Gtk.ListBox, search_box: Gtk.SearchEntry):
        self.recent_list_box = recent_list
        self.search_box = search_box
        self.recent_searches: Dict[str, RecentSearchRow] = {}
        self.recent_list_box.connect('row-activated', self._row_clicked)

    def add_new_recent_search(self, text: str):
        if not text:
            return

        if text in self.recent_searches:
            old_row = self.recent_searches[text]
            # move to top of the list
            self.recent_list_box.remove(old_row)
            self.recent_list_box.insert(old_row, 0)
            return

        if len(self.recent_searches) == self.SEARCH_VALUES_TO_KEEP:
            last_row: RecentSearchRow = self.recent_list_box.get_children()[-1]
            del self.recent_searches[last_row.search_text]
            self.recent_list_box.remove(last_row)

        row = RecentSearchRow(text)
        self.recent_list_box.insert(row, 0)
        self.recent_searches[text] = row

    def _row_clicked(self, _widget, row: RecentSearchRow):
        self.search_box.set_text(row.search_text)

class SearchPage(MenuPage):
    """
    Helper class for managing the Search menu page.
    """
    def __init__(self, vm_manager: VMManager, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager):
        """
        :param vm_manager: VM Manager object
        :param builder: Gtk.Builder with loaded glade object
        :param desktop_file_manager: Desktop File Manager object
        """
        self.vm_manager = vm_manager
        self.desktop_file_manager = desktop_file_manager

        self.vm_list: Gtk.ListBox = builder.get_object('search_vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('search_app_list')
        self.search_entry: Gtk.SearchEntry = builder.get_object('search_entry')

        self.search_entry.connect('search-changed', self._do_search)

        desktop_file_manager.register_callback(self._app_info_callback)

        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect('row-activated', self._app_clicked)

        vm_manager.register_new_vm_callback(self._vm_callback)
        self.vm_list.set_filter_func(self._is_vm_fitting)

        # TODO: improve vm search
        self.app_list.set_sort_func(self._sort_apps)
        self.vm_list.set_sort_func(lambda x, y: x.sort_order > y.sort_order)
        self.app_list.invalidate_sort()
        self.vm_list.invalidate_sort()

        self.recent_list: Gtk.ListBox = builder.get_object('search_recent_list')

        self.app_view: Gtk.ScrolledWindow = builder.get_object("search_app_view")
        self.vm_view: Gtk.ScrolledWindow = builder.get_object("search_vm_view")
        self.recent_view: Gtk.ScrolledWindow = \
            builder.get_object("search_recent_view")
        self.recent_title: Gtk.Label = builder.get_object('search_recent_title')

        self.recent_search_manager = RecentSearchManager(
            self.recent_list, self.search_entry)

        # self.vm_list.connect('row-selected', self._vm_selected)

    def _app_clicked(self, _widget, row):
        self.recent_search_manager.add_new_recent_search(
            self.search_entry.get_text())
        row.run_app(row.app_info.vm)

    def _app_info_callback(self, app_info):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        if app_info.vm or not app_info.is_qubes_specific():
            entry = AppEntryWithVM(app_info, self.vm_manager)
            app_info.entries.append(entry)
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
        self.vm_view.set_visible(has_search)
        self.app_view.set_visible(has_search)
        self.recent_view.set_visible(not has_search)
        self.recent_title.set_visible(not has_search)

        self.vm_list.invalidate_filter()
        self.vm_list.invalidate_sort()
        self.app_list.invalidate_filter()
        self.app_list.invalidate_sort()

    def _sort_apps(self, appentry: AppEntryWithVM, other_entry: AppEntryWithVM):
        """
        # word is delineated by space and - and _
        Sorting algorithm:
        * if any searched word is at the beginning of a word in the app
         name or vm name, the app should be before apps for which this
          is not true
        *
        """
        search_text = self.search_entry.get_text()
        result_1 = appentry.find_text(search_text)
        result_2 = other_entry.find_text(search_text)
        if result_1 > result_2:
            return -1
        if result_1 < result_2:
            return 1
        return 0

# TESTING CASES:
    # work firefox
    # firefox
    # firefox work
    # fire work
    # py dev
    # gpg term
    # term dom0
    # sys-net term
    # net term
    # pi

    def _is_app_fitting(self, appentry: AppEntryWithVM):
        """Show only apps matching the current search text"""
        return appentry.find_text(self.search_entry.get_text()) > 0

    def _is_vm_fitting(self, vmrow: SearchVMRow):
        """Show only vms matching the current search text"""
        # possible options
        # 1. show all vms where a matching app was found
        # (add a fake ALL option on top, filtering right by found vm)
        # 2. show all vms whose names match all search terms
        # (what happens on click?)
        # 3. show all vms whose names match at least one search term
        # (all happens on click)
        return vmrow.find_text(self.search_entry.get_text()) > 0

    def initialize_page(self):
        """
        Initialize own state.
        """
        self.search_entry.set_text('')
        self.app_view.set_visible(False)
        self.vm_view.set_visible(False)
        self.recent_view.set_visible(True)

        self.app_list.invalidate_filter()
        self.vm_list.invalidate_filter()
        self.search_entry.grab_focus_without_selecting()
