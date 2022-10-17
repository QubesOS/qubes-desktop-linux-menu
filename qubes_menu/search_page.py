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
from typing import List

from .desktop_file_manager import DesktopFileManager
from .custom_widgets import VMRow
from .app_widgets import AppEntry, AppEntryWithVM
from .vm_manager import VMEntry, VMManager
from .page_handler import MenuPage

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


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

        # TODO: improve
        self.app_list.set_sort_func(self._sort_apps)
        self.vm_list.set_sort_func(lambda x, y: x.sort_order > y.sort_order)
        self.app_list.invalidate_sort()
        self.vm_list.invalidate_sort()

        # self.vm_list.connect('row-selected', self._vm_selected)

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
            vm_row = VMRow(vm_entry)
            vm_row.show_all()
            vm_entry.entries.append(vm_row)
            self.vm_list.add(vm_row)
            self.vm_list.invalidate_filter()
            self.vm_list.invalidate_sort()

    def _do_search(self, *_args):
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
        result_1 = self._text_search(search_text, appentry.search_words)
        result_2 = self._text_search(search_text,
                                     other_entry.search_words)
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

    def _is_app_fitting(self, appentry: AppEntryWithVM):
        """Show only apps matching the current search text"""
        return self._text_search(
            self.search_entry.get_text(), appentry.search_words) > 0

    def _is_vm_fitting(self, vmrow: VMRow):
        """Show only vms matching the current search text"""
        return self._text_search(self.search_entry.get_text(),
                          vmrow.search_words) > 0

    @staticmethod
    def _text_search(search_phrase: str, text_words: List[str]):
        """Text-searching function.
        Returns a match rank, if greater than 0, the searched phrase was found.
        The higher the number, the better the match.
        All words from the searched phrase must have been found.
        """
        result = 0
        if not search_phrase:
            return result

        search_words = search_phrase.lower().split(' ')

        for search_word in search_words:
            for text_word in text_words:
                if text_word.startswith(search_word):
                    result += 1
                    break
                elif search_word in text_word:
                    result += 0.5
                    break
            else:
                return 0
        return result

    def _app_clicked(self, _widget: Gtk.Widget, row: AppEntry):
        row.run_app(row.app_info.vm)

    def initialize_page(self):
        """
        Initialize own state.
        """
        self.search_entry.set_text('')
        self.app_list.invalidate_filter()
        self.vm_list.invalidate_filter()
        self.search_entry.grab_focus_without_selecting()
