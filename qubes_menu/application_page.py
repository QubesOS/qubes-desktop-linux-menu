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
import subprocess
from typing import Optional

import qubesadmin.events

from .desktop_file_manager import DesktopFileManager
from .custom_widgets import LimitedWidthLabel, NetworkIndicator, \
    SettingsEntry, HoverListBox
from .app_widgets import AppEntry, BaseAppEntry
from .vm_manager import VMEntry, VMManager
from .utils import load_icon

# pylint: disable=wrong-import-position
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class VMRow(HoverListBox):
    def __init__(self, vm_entry: VMEntry, qapp: qubesadmin.Qubes):
        super().__init__()
        self.qapp = qapp
        self.vm_entry = vm_entry
        self.get_style_context().add_class('vm_entry')

        self.icon_img = Gtk.Image()

        self.main_box.pack_start(self.icon_img, False, False, 2)
        self.main_box.pack_start(
            Gtk.Label(label=self.vm_entry.vm_name), False, False, 2)

        self.update_contents(update_power_state=True, update_label=True,
                             update_has_network=True, update_type=True)

    def _update_style(self):
        style_context: Gtk.StyleContext = self.get_style_context()
        if self.vm_entry.is_dispvm_template:
            style_context.add_class('dvm_template_entry')
        elif self.vm_entry.vm_klass == 'DispVM':
            style_context.add_class('dispvm_entry')
        else:
            if style_context.has_class('dispvm_entry'):
                style_context.remove_class('dispvm_entry')
            if style_context.has_class('dvm_template_entry'):
                style_context.remove_class('dvm_template_entry')

        if self.vm_entry.power_state == 'Running':
            style_context.add_class('running_vm')
        else:
            if style_context.has_class('running_vm'):
                style_context.remove_class('running_vm')

    def update_contents(self,
                        update_power_state=False,
                        update_label=False,
                        update_has_network=False,
                        update_type=False):
        if update_label:
            icon_vm = load_icon(self.vm_entry.vm_icon_name)
            self.icon_img.set_from_pixbuf(icon_vm)
        if update_type or update_power_state:
            self._update_style()
            if self.get_parent():
                self.get_parent().invalidate_sort()
                self.get_parent().invalidate_filter()
        if update_has_network:
            if self.is_selected() and self.get_parent():
                self.get_parent().select_row(None)
                self.get_parent().select_row(self)
        self.main_box.show_all()

    @property
    def sort_order(self):
        return self.vm_entry.sort_name


class ControlRow(Gtk.ListBoxRow):
    def __init__(self):
        super().__init__()
        self.row_label = LimitedWidthLabel()
        self.get_style_context().add_class('app_entry')
        self.add(self.row_label)
        self.command = None

    def update_state(self, state):
        pass

    def run_app(self, vm):
        if self.command and self.is_sensitive():
            subprocess.Popen([self.command, str(vm)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)


class StartControlItem(ControlRow):
    def __init__(self):
        super().__init__()
        self.state = None

    def update_state(self, state):
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
    def __init__(self):
        super().__init__()
        self.state = None

    def update_state(self, state):
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
    def __init__(self, app_page):
        super().__init__()
        self.app_page = app_page

        self.get_style_context().add_class('right_pane')

        self.start_item = StartControlItem()

        self.add(self.start_item)
        self.add(PauseControlItem())

    def update_visibility(self, state):
        for row in self.get_children():
            row.update_state(state)


class VMTypeToggle:
    def __init__(self, builder: Gtk.Builder, qapp: qubesadmin.Qubes):
        self.apps_toggle: Gtk.RadioButton = builder.get_object('apps_toggle')
        self.templates_toggle: Gtk.RadioButton = \
            builder.get_object('templates_toggle')
        self.system_toggle: Gtk.RadioButton = \
            builder.get_object('system_toggle')
        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')
        self.qapp = qapp

        self.buttons = [self.apps_toggle, self.templates_toggle,
                        self.system_toggle]

        for button in self.buttons:
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            button.set_can_focus(True)
            button.connect('focus', self._activate_button)

    def initialize_state(self):
        self.apps_toggle.set_active(True)

        for button in self.buttons:
            if button.get_size_request() == (-1, -1):
                button.set_size_request(button.get_allocated_width()*1.2, -1)

    @staticmethod
    def _activate_button(widget, _event):
        widget.set_active(True)

    def connect_to_toggle(self, func):
        for button in self.buttons:
            button.connect('toggled', func)

    def filter_function(self, row):
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
        if vm_entry.provides_network:
            return False
        if vm_entry.vm_klass == 'TemplateVM':
            return False
        return True

    @staticmethod
    def _filter_templatevms(vm_entry: VMEntry):
        if vm_entry.vm_klass == 'TemplateVM':
            return True
        return vm_entry.is_dispvm_template

    @staticmethod
    def _filter_service(vm_entry: VMEntry):
        return vm_entry.provides_network


class AppPage:
    def __init__(self, qapp: qubesadmin.Qubes, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher):
        self.qapp = qapp
        self.dispatcher = dispatcher
        self.desktop_file_manager = desktop_file_manager
        self.selected_vm_entry: Optional[VMRow] = None

        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')
        self.settings_list: Gtk.ListBox = builder.get_object('settings_list')
        self.vm_right_pane: Gtk.Box = builder.get_object('vm_right_pane')

        self.network_indicator = NetworkIndicator()
        self.vm_right_pane.pack_start(self.network_indicator, False, False, 0)
        self.vm_right_pane.reorder_child(self.network_indicator, 0)

        self.desktop_file_manager.register_callback(self._app_info_callback)
        self.toggle_buttons = VMTypeToggle(builder, self.qapp)
        self.toggle_buttons.connect_to_toggle(self._button_toggled)

        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect('row-activated', self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        self.app_list.invalidate_sort()

        self.vm_manager = VMManager(self.qapp, self.dispatcher)
        self.vm_manager.register_new_vm_callback(self._vm_callback)
        self.vm_list.set_sort_func(lambda x, y: x.sort_order > y.sort_order)
        self.vm_list.set_filter_func(self.toggle_buttons.filter_function)

        self.vm_list.connect('row-selected', self._selection_changed)

        self.settings_list.add(SettingsEntry())
        self.settings_list.connect('row-activated', self._app_clicked)

        self.control_list = ControlList(self)
        self.control_list.connect('row-activated', self._app_clicked)
        self.vm_right_pane.pack_end(self.control_list, False, False, 0)

        self._set_keyboard_focus_chain()
        self.app_list.connect('keynav-failed', self._keynav_failed)
        self.settings_list.connect('keynav-failed', self._keynav_failed)
        self.control_list.connect('keynav-failed', self._keynav_failed)
        self.app_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.settings_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.control_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.widget_order = [self.settings_list, self.app_list,
                             self.control_list]

    def _app_info_callback(self, app_info):
        if app_info.vm:
            entry = BaseAppEntry(app_info)
            app_info.entries.append(entry)
            self.app_list.add(entry)

    def _vm_callback(self, vm_entry: VMEntry):
        if vm_entry:
            vm_row = VMRow(vm_entry, self.qapp)
            vm_row.show_all()
            vm_entry.entries.append(vm_row)
            self.vm_list.add(vm_row)
            self.vm_list.invalidate_filter()
            self.vm_list.invalidate_sort()
# TODO: weird bug in file manager system entry

    def _is_app_fitting(self, appentry: BaseAppEntry):
        # TODO: is this too complex?
        # TODO: debug what happens when a VM becomes a dvm template
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
        # pylint: disable=attribute-defined-outside-init
        # this is a hacky way to make finding neighbouring widgets less annoying
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

    def _get_direction_child(self, widget: Gtk.ListBox,
                             direction: Gtk.DirectionType):
        child_list = widget.get_children()
        if direction == Gtk.DirectionType.UP:
            child_list = reversed(child_list)
        for child in child_list:
            if widget != self.app_list or self._is_app_fitting(child):
                return child
        return widget.get_row_at_index(0)

    def _keynav_failed(self, widget: Gtk.ListBox, direction: Gtk.DirectionType):
        next_widget_dict = getattr(widget, 'focus_neighbors', None)
        if not next_widget_dict:
            return
        next_widget = next_widget_dict.get(direction, None)
        if not next_widget:
            return
        next_focus_widget = self._get_direction_child(next_widget, direction)
        next_focus_widget.grab_focus()

    def _app_clicked(self, _widget: Gtk.Widget, row: AppEntry):
        if not self.selected_vm_entry:
            return
        row.run_app(self.selected_vm_entry.vm_entry.vm)

    def _button_toggled(self, widget: Gtk.ToggleButton):
        if not widget.get_active():
            return
        self.vm_list.select_row(None)
        self.app_list.invalidate_filter()
        self.vm_list.invalidate_filter()

    def initialize_state(self, _vm=None):
        self.toggle_buttons.initialize_state()
        self.app_list.select_row(None)
        self.control_list.hide()
        self.settings_list.hide()

    def _selection_changed(self, _widget, row: Optional[VMRow]):
        if row is None:
            self.selected_vm_entry = None
            self.control_list.hide()
            self.settings_list.hide()
            self.network_indicator.set_visible(False)
            return
        self.selected_vm_entry = row
        self.control_list.show_all()
        self.settings_list.show_all()
        self.app_list.invalidate_filter()
        self.control_list.update_visibility(row.vm_entry.power_state)
        self.control_list.select_row(None)
        self.app_list.ephemeral_vm = bool(
            self.selected_vm_entry.vm_entry.parent_vm)
        self.network_indicator.set_network_state(row.vm_entry.has_network)
