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

        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        self.vm_list.set_sort_func(lambda x, y: x.sort_order > y.sort_order)
        self.app_list.invalidate_sort()
        self.vm_list.invalidate_sort()

        # self.vm_list.connect('row-selected', self._vm_selected)

    def _app_info_callback(self, app_info):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        if app_info.vm:
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
        self.app_list.invalidate_filter()

    def _is_app_fitting(self, appentry: AppEntryWithVM):
        """
        Filter function for applications - attempts to filter only
        applications that have a VM same as selected VM, or, in the case
        of disposable VMs that are children of a parent DVM template,
        show the DVM's menu entries.
        """
        search_text = self.search_entry.get_text()
        if not search_text:
            return False

        words = search_text.split(' ')
        text_to_look_in = (getattr(appentry.app_info.vm, 'name') or '') + \
                          ' ' + (appentry.app_info.app_name or '')
        for word in words:
            if word not in text_to_look_in:
                return False
        return True

    def _is_vm_fitting(self, vmrow: VMRow):
        search_text = self.search_entry.get_text()
        if not search_text:
            return False

        words = search_text.split(' ')
        text_to_look_in = vmrow.vm_entry.vm_name

        for word in words:
            if word not in text_to_look_in:
                return False
        return True

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
