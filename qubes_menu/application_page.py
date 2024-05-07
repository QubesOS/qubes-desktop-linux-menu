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
import subprocess
from typing import Optional

from .desktop_file_manager import DesktopFileManager
from .custom_widgets import LimitedWidthLabel, NetworkIndicator, \
    SettingsEntry, VMRow, HoverEventBox
from .app_widgets import AppEntry, BaseAppEntry
from .vm_manager import VMEntry, VMManager
from .page_handler import MenuPage
from .utils import get_visible_child

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
        self.event_box = HoverEventBox(focus_widget=self)
        self.add(self.event_box)
        self.event_box.add(self.row_label)
        self.show_all()
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
            # pylint: disable=consider-using-with
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

        self.get_style_context().add_class('right_pane')

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


class VMTypeToggle:
    """
    A class controlling a set of radio buttons for toggling
    which VMs are shown.
    """
    def __init__(self, builder: Gtk.Builder):
        """
        :param builder: Gtk.Builder, containing loaded glade data
        """
        self.apps_toggle: Gtk.RadioButton = builder.get_object('apps_toggle')
        self.templates_toggle: Gtk.RadioButton = \
            builder.get_object('templates_toggle')
        self.system_toggle: Gtk.RadioButton = \
            builder.get_object('system_toggle')
        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')

        self.buttons = [self.apps_toggle, self.templates_toggle,
                        self.system_toggle]

        for button in self.buttons:
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            button.set_can_focus(True)
            # the below is necessary to make sure keyboard navigation
            # behaves correctly
            button.connect('focus', self._activate_button)

    def initialize_state(self):
        """
        Initialize own state; by default Apps section is selected.
        Furthermore, it increases space allocated to widgets to make sure
        no problems happen when hover effect is applied
        (by default hover is a couple of pixels wider than non-hover, and
        Gtk wants to dynamically change button length... leading to the whole
        pane's size oscillating.)
        """
        self.apps_toggle.set_active(True)

        for button in self.buttons:
            if button.get_size_request() == (-1, -1):
                button.set_size_request(button.get_allocated_width()*1.2, -1)

    def grab_focus(self):
        """Simulates other grab_focus type functions: grabs keyboard focus
        to currently selected toggle"""
        for button in self.buttons:
            if button.get_active():
                button.grab_focus()
                return

    @staticmethod
    def _activate_button(widget, _event):
        """Helper function that activates triggering widget. Used in keyboard
        navigation to activate on focus."""
        widget.set_active(True)

    def connect_to_toggle(self, func):
        """Connect a function to toggling of all buttons"""
        for button in self.buttons:
            button.connect('toggled', func)

    def filter_function(self, row):
        """Filter function calculated based on currently selected VM toggle
        button. Used in filtering VM list placed outside this widget."""
        vm_entry: VMEntry = row.vm_entry

        if self.apps_toggle.get_active():
            return self._filter_appvms(vm_entry)
        if self.templates_toggle.get_active():
            return self._filter_templatevms(vm_entry)
        if self.system_toggle.get_active():
            return self._filter_service(vm_entry)
        return False

    @staticmethod
    def _filter_appvms(vm_entry: VMEntry):
        """
        Filter function for normal / application VMEntries. Returns VMs that
        are not a templateVM and do not provide network.
        """
        return vm_entry.show_in_apps

    @staticmethod
    def _filter_templatevms(vm_entry: VMEntry):
        """
        Filter function for template VMEntries. Returns VMs that
        are a templateVM or a template for DispVMs.
        """
        if vm_entry.vm_klass == 'TemplateVM':
            return True
        return vm_entry.is_dispvm_template

    @staticmethod
    def _filter_service(vm_entry: VMEntry):
        """
        Filter function for service/system VMEntries. Returns VMs that
        have feature 'servicevm' set.
        """
        return vm_entry.service_vm


class AppPage(MenuPage):
    """
    Helper class for managing the entirety of Applications menu page.
    """
    def __init__(self, vm_manager: VMManager, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager):
        """
        :param vm_manager: VM Manager object
        :param builder: Gtk.Builder with loaded glade object
        :param desktop_file_manager: Desktop File Manager object
        """
        self.selected_vm_entry: Optional[VMRow] = None
        self.sort_running = False # Sort running VMs to top

        self.page_widget: Gtk.Box = builder.get_object("app_page")

        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')
        self.settings_list: Gtk.ListBox = builder.get_object('settings_list')
        self.vm_right_pane: Gtk.Box = builder.get_object('vm_right_pane')
        self.separator_top = builder.get_object('separator_top')
        self.separator_bottom = builder.get_object('separator_bottom')

        self.network_indicator = NetworkIndicator()
        self.vm_right_pane.pack_start(self.network_indicator, False, False, 0)
        self.vm_right_pane.reorder_child(self.network_indicator, 0)

        desktop_file_manager.register_callback(self._app_info_callback)
        self.toggle_buttons = VMTypeToggle(builder)
        self.toggle_buttons.connect_to_toggle(self._button_toggled)

        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect('row-activated', self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y:
            x.app_info.sort_name > y.app_info.sort_name)
        self.app_list.invalidate_sort()

        vm_manager.register_new_vm_callback(self._vm_callback)
        self.vm_list.set_sort_func(self._sort_vms)
        self.vm_list.set_filter_func(self.toggle_buttons.filter_function)

        self.vm_list.connect('row-selected', self._selection_changed)

        self.settings_list.add(SettingsEntry())
        self.settings_list.connect('row-activated', self._app_clicked)

        self.control_list = ControlList(self)
        self.control_list.connect('row-activated', self._app_clicked)
        self.vm_right_pane.pack_end(self.control_list, False, False, 0)

        self.setup_keynav()

        self.app_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.settings_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.control_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.widget_order = [self.settings_list, self.app_list,
                             self.control_list]

        self.vm_list.select_row(None)
        self._selection_changed(None, None)

        self.vm_list.connect('map', self._on_map_vm_list)

    def _on_map_vm_list(self, *_args):
        # workaround for https://gitlab.gnome.org/GNOME/gtk/-/issues/4977
        # doesn't always fix it on the first try, but improves behavior in
        # case of unexpected focus chain changes, like pgup in some cases
        self.vm_list.select_row(self.vm_list.get_row_at_y(0))
        self.app_list.set_filter_func(None)
        self.app_list.invalidate_filter()
        self.app_list.set_filter_func(self._is_app_fitting)

    def _sort_vms(self, vmentry: VMRow, other_entry: VMRow):
        if self.sort_running:
            if vmentry.vm_entry.power_state != other_entry.vm_entry.power_state:
                if vmentry.vm_entry.power_state == "Running":
                    return -1
                return 1
        return vmentry.sort_order > other_entry.sort_order

    def set_sorting_order(self, sort_running: bool = False):
        self.sort_running = sort_running
        self.vm_list.invalidate_sort()

    def setup_keynav(self):
        """Do all the required faffing about to convince Gtk to have
        reasonable keyboard nav"""
        self._set_keyboard_focus_chain()

        self.app_list.connect('keynav-failed', self._keynav_failed)
        self.settings_list.connect('keynav-failed', self._keynav_failed)
        self.control_list.connect('keynav-failed', self._keynav_failed)
        self.vm_list.connect('keynav-failed', self._vm_keynav_failed)

        self.app_list.connect('key-press-event', self._focus_vm_list)
        self.settings_list.connect('key-press-event', self._focus_vm_list)
        self.control_list.connect('key-press-event', self._focus_vm_list)

        self.vm_list.connect('key-press-event', self._vm_key_pressed)

    def _vm_key_pressed(self, _widget, event):
        if event.keyval == Gdk.KEY_Right:
            child = get_visible_child(self.app_list)
            if child:
                child.grab_focus()
                return True
        return False

    def _app_info_callback(self, app_info):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        if app_info.vm:
            entry = BaseAppEntry(app_info)
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

    def _is_app_fitting(self, appentry: BaseAppEntry):
        """
        Filter function for applications - attempts to filter only
        applications that have a VM same as selected VM, or, in the case
        of disposable VMs that are children of a parent DVM template,
        show the DVM's menu entries.
        """
        if not self.selected_vm_entry:
            return False
        if appentry.app_info.vm and \
                appentry.app_info.vm.name != \
                self.selected_vm_entry.vm_entry.vm_name:
            return self.selected_vm_entry.vm_entry.parent_vm == \
                   appentry.app_info.vm.name and \
                   not appentry.app_info.disposable
        if self.selected_vm_entry.vm_entry.is_dispvm_template:
            return appentry.app_info.disposable == \
                   self.toggle_buttons.apps_toggle.get_active()
        return True

    def _set_keyboard_focus_chain(self):
        """
        A somewhat hacky helper function that is used by keyboard navigation
        functions.
        """
        # pylint: disable=attribute-defined-outside-init
        self.control_list.focus_neighbors = {
            Gtk.DirectionType.UP: self.app_list,
            Gtk.DirectionType.DOWN: self.settings_list,
        }
        self.app_list.focus_neighbors = {
            Gtk.DirectionType.UP: self.settings_list,
            Gtk.DirectionType.DOWN: self.control_list,
        }
        self.settings_list.focus_neighbors = {
            Gtk.DirectionType.UP: self.control_list,
            Gtk.DirectionType.DOWN: self.app_list,
        }

    def _vm_keynav_failed(self, _widget, direction: Gtk.DirectionType):
        if direction == Gtk.DirectionType.UP:
            self.toggle_buttons.grab_focus()

    def _keynav_failed(self, widget: Gtk.ListBox, direction: Gtk.DirectionType):
        """
        Callback to be performed when keyboard nav fails. Attempts to
        find next widget and move keyboard focus to it.
        """
        next_widget_dict = getattr(widget, 'focus_neighbors', None)
        if not next_widget_dict:
            return
        next_widget = next_widget_dict.get(direction, None)
        if not next_widget:
            return
        next_focus_widget = get_visible_child(
            next_widget, reverse=direction == Gtk.DirectionType.UP)
        if next_focus_widget:
            next_focus_widget.grab_focus()

    def _focus_vm_list(self, _widget, event):
        """Move focus to VM list"""
        if event.keyval == Gdk.KEY_Left:
            self.vm_list.get_selected_row().grab_focus()
            return True
        return False

    def _app_clicked(self, _widget: Gtk.Widget, row: AppEntry):
        if not self.selected_vm_entry:
            return
        row.run_app(self.selected_vm_entry.vm_entry.vm)

    def _button_toggled(self, widget: Gtk.ToggleButton):
        if not widget.get_active():
            return
        self.vm_list.unselect_all()
        self.app_list.invalidate_filter()
        self.vm_list.invalidate_filter()

    def initialize_page(self):
        """
        Initialize own state.
        """
        self.toggle_buttons.initialize_state()
        self.vm_list.unselect_all()
        self.app_list.unselect_all()

    def _selection_changed(self, _widget, row: Optional[VMRow]):
        if row is None:
            self.vm_list.unselect_all()
            self.selected_vm_entry = None
            self.app_list.ephemeral_vm = False
            self._set_right_visibility(False)
        else:
            self.selected_vm_entry = row
            self._set_right_visibility(True)
            self.network_indicator.set_network_state(row.vm_entry.has_network)
            self.control_list.update_visibility(row.vm_entry.power_state)
            self.control_list.unselect_all()
            self.app_list.ephemeral_vm = bool(
                self.selected_vm_entry.vm_entry.parent_vm)
        self.app_list.invalidate_filter()

    def _set_right_visibility(self, visibility: bool):
        self.vm_right_pane.set_visible(visibility)
        self.control_list.set_visible(visibility)
        self.app_list.set_visible(visibility)
        self.settings_list.set_visible(visibility)
        self.separator_top.set_visible(visibility)
        self.separator_bottom.set_visible(visibility)
        if not visibility:
            self.network_indicator.set_visible(False)
