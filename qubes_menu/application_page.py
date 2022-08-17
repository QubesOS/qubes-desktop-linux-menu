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
Application page and related widgets and logic
"""
from lib2to3.pytree import Base
import subprocess
from typing import Dict, Optional, List

import qubesadmin.events
from qubesadmin.vm import QubesVM

from . import constants
from .desktop_file_manager import DesktopFileManager, ApplicationInfo
from .custom_widgets import LimitedWidthLabel, NetworkIndicator, \
    SettingsEntry, HoverListBox
from .app_widgets import AppEntry, BaseAppEntry
from .vm_manager import VMEntry, VMManager
from .utils import load_icon

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class ControlRow(Gtk.ListBoxRow):
    """
    Gtk.ListBoxRow representing one of the VM control options: start/shutdown/
    pause etc.
    """
    def __init__(self):
        super().__init__()
        self.row_label = LimitedWidthLabel()
        self.get_style_context().add_class('app_entry')
        self.add(self.row_label)
        self.command = None

    def update_state(self, state):
        """
        Update own state (visibility/text/sensitivity) based on provided VM
        state.
        """

    def run_app(self, vm):
        """
        Run related app/script.
        """
        if self.command and self.is_sensitive():
            subprocess.Popen([self.command, str(vm)], stdin=subprocess.DEVNULL)


class StartControlItem(ControlRow):
    """
    Control Row item representing changing VM state: start if it's not running,
    shutdown if it's running, unpause if it's paused, and kill if it's
    transient.
    """
    def __init__(self):
        super().__init__()
        self.state = None

    def update_state(self, state):
        """
        Update own state (visibility/text/sensitivity) based on provided VM
        state.
        """
        self.state = state
        if state == 'Running':
            self.row_label.set_label('Shutdown qube')
            self.command = 'qvm-shutdown'
            return
        if state == 'Transient':
            self.row_label.set_label('Kill qube')
            self.command = 'qvm-kill'
            return
        if state == 'Halted':
            self.row_label.set_label('Start qube')
            self.command = 'qvm-start'
            return
        if state == 'Paused':
            self.row_label.set_label('Unpause qube')
            self.command = 'qvm-unpause'
            return


class PauseControlItem(ControlRow):
    """
    Control Row item representing pausing VM: visible only when it's running.
    """
    def __init__(self):
        super().__init__()
        self.state = None

    def update_state(self, state):
        """
        Update own state (visibility/text/sensitivity) based on provided VM
        state.
        """
        self.state = state
        if state == 'Running':
            self.row_label.set_label('Pause qube')
            self.set_sensitive(True)
            self.command = 'qvm-pause'
            return
        self.row_label.set_label(' ')
        self.set_sensitive(False)
        self.command = None


class ControlList(Gtk.ListBox):
    """
    ListBox containing VM state control items.
    """
    def __init__(self, app_page):
        super().__init__()
        self.app_page = app_page

        self.get_style_context().add_class('apps_pane')

        self.start_item = StartControlItem()
        self.pause_item = PauseControlItem()

        self.add(self.start_item)
        self.add(self.pause_item)

    def update_visibility(self, state):
        """
        Update children's state based on provided VM state.
        """
        for row in self.get_children():
            row.update_state(state)


class AppPage(Gtk.Box):
    """
    Helper class for managing the entirety of Applications menu page.
    """
    def __init__(self,
                 vm_entry,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher):
        """
        :param vm_manager: VM Manager object
        :param builder: Gtk.Builder with loaded glade object
        :param desktop_file_manager: Desktop File Manager object
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.get_style_context().add_class('apps_pane')

        self.vm_entry: VMEntry = vm_entry

        self.vm_apps = dict()
        
        self.settings_list: Gtk.ListBox = Gtk.ListBox()
        self.settings_list.get_style_context().add_class('apps_pane')
        self.settings_list.add(SettingsEntry())
        self.settings_list.connect('row-activated', self._app_clicked)

        self.scrolled_window: Gtk.ScrolledWindow = Gtk.ScrolledWindow()
        self.scrolled_window.get_style_context().add_class('apps_pane')
        
        self.view_port: Gtk.Viewport = Gtk.Viewport()
        self.scrolled_window.add(self.view_port)
        self.scrolled_window.set_min_content_width(410)
        
        self.app_list: Gtk.ListBox = Gtk.ListBox()
        self.app_list.get_style_context().add_class('apps_pane')
        self.app_list.connect('row-activated', self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name
        )
        self.app_list.invalidate_sort()
        self.view_port.add(self.app_list)

        self.separator_top: Gtk.Separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.separator_bottom: Gtk.Separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)

        self.network_indicator = NetworkIndicator()
        self.network_indicator.set_network_state(self.vm_entry.has_network)

        self.control_list = ControlList(self)
        self.control_list.connect('row-activated', self._app_clicked)
        self.control_list.update_visibility(self.vm_entry.power_state)

        self.dispatcher = dispatcher
        self.dispatcher.add_handler(
            f'domain-feature-pre-set:{constants.FAVORITES_FEATURE}',
            self._update_fav_btn
        )

        self.desktop_file_manager = desktop_file_manager
        self.desktop_file_manager.register_callback(self._app_info_callback)

        self.pack_start(self.network_indicator, False, False, 0)
        self.pack_start(self.settings_list, False, True, 0)
        self.pack_start(self.separator_top, False, True, 0)
        self.pack_start(self.scrolled_window, True, True, 0)
        self.pack_start(self.separator_bottom, False, True, 0)
        self.pack_start(self.control_list, False, True, 0)

        self.show_all()
        
    def _update_fav_btn(self, vm, event, feature, *_args, **_kwargs):
        """
        Update the favorite buttons in the app page
        """
        if str(vm) == self.vm_entry.vm_name:
            old_fav = _kwargs['oldvalue'].split(' ') if _kwargs['oldvalue'] else None
            new_fav = _kwargs['value'].split(' ')

            if old_fav and len(old_fav) > len(new_fav) or new_fav == ['']:
                remove_fav = list(set(old_fav) - set(new_fav))[0]
                self.vm_apps[remove_fav].update_fav_btn()

    def _app_clicked(self, _widget: Gtk.Widget, row: AppEntry):
        if not self.vm_entry:
            return
        row.run_app(self.vm_entry.vm)
        self.control_list.update_visibility(self.vm_entry.power_state)

    
    def _app_info_callback(self, app_info: ApplicationInfo):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        if app_info.vm:          
            if app_info.vm == self.vm_entry.vm:
                entry = BaseAppEntry(app_info)

                self.vm_apps[entry.app_info.entry_name] = entry

                app_info.entries.append(entry)
                self.app_list.add(entry)
                self.app_list.show_all()

