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


class VMRow(HoverListBox):
    """
    Helper widget representing a VM row.
    """
    def __init__(self, vm_entry: VMEntry):
        """
        :param vm_entry: VMEntry object, stored and managed by VMManager
        """
        super().__init__()
        self.vm_entry = vm_entry
        self.get_style_context().add_class('vm_entry')

        self.icon_img = Gtk.Image()

        self.main_box.pack_start(self.icon_img, False, False, 2)
        self.main_box.pack_start(
            Gtk.Label(label=self.vm_entry.vm_name), False, False, 2)

        self.update_contents(update_power_state=True, update_label=True,
                             update_has_network=True, update_type=True)

    def _update_style(self):
        """Update own style, based on whether VM is running or not and
        what type it has."""
        style_context: Gtk.StyleContext = self.get_style_context()
        if self.vm_entry.is_dispvm_template:
            style_context.add_class('dvm_template_entry')
        elif self.vm_entry.vm_klass == 'DispVM':
            style_context.add_class('dispvm_entry')
        else:
            style_context.remove_class('dispvm_entry')
            style_context.remove_class('dvm_template_entry')

        if self.vm_entry.power_state == 'Running':
            style_context.add_class('running_vm')
        else:
            style_context.remove_class('running_vm')

    def update_contents(self,
                        update_power_state=False,
                        update_label=False,
                        update_has_network=False,
                        update_type=False):
        """
        Update own contents (or related widgets, if applicable) based on state
        change.
        :param update_power_state: whether to update if VM is running or not
        :param update_label: whether label (vm icon) should be updated
        :param update_has_network: whether VM networking state should be
        updated
        :param update_type: whether VM type should be updated
        :return:
        """
        if update_label:
            icon_vm = load_icon(self.vm_entry.vm_icon_name)
            self.icon_img.set_from_pixbuf(icon_vm)
        if update_type or update_power_state:
            self._update_style()
            if self.get_parent():
                self.get_parent().invalidate_sort()
                self.get_parent().invalidate_filter()
                self.get_parent().select_row(None)
        if update_has_network:
            if self.is_selected() and self.get_parent():
                self.get_parent().select_row(None)
                self.get_parent().select_row(self)
        self.main_box.show_all()

    @property
    def sort_order(self):
        """
        Helper property exposing desired sort order.
        """
        return self.vm_entry.sort_name


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
        self.tools_toggle: Gtk.RadioButton = \
            builder.get_object('tools_toggle')
        self.service_toggle: Gtk.RadioButton = \
            builder.get_object('service_toggle')
        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')

        self.buttons = [self.apps_toggle, self.tools_toggle,
                        self.service_toggle]

        for button in self.buttons:
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            button.set_can_focus(True)
            # the below is necessary to make sure keyboard navigation
            # behaves corrrectly
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
        if type(row) == VMRow:
            vm_entry: VMEntry = row.vm_entry

            if self.apps_toggle.get_active():
                return self._filter_appvms(vm_entry)
            if self.service_toggle.get_active():
                return self._filter_service(vm_entry)
        elif type(row) == BaseAppEntry:
            if self.tools_toggle.get_active():
                return self._filter_tools(row)
            
        return False

    @staticmethod
    def _filter_tools(row: BaseAppEntry):
        if 'X-XFCE-SettingsDialog' not in row.app_info.categories:
            return False
        return 'qubes' in row.app_info.entry_name

    @staticmethod
    def _filter_appvms(vm_entry: VMEntry):
        """
        Filter function for normal / application VMEntries. Returns VMs that
        are not a templateVM and do not provide network.
        """
        if vm_entry.service_vm:
            return False
        if vm_entry.vm_klass == 'TemplateVM':
            return False
        return True

    @staticmethod
    def _filter_templatevms(vm_entry: VMEntry):
        """
        Filter function for template VMEntries. Returns VMs that
        are a templateVM or a template for DispVMs.
        """
        if vm_entry.vm_klass == 'TemplateVM':
            return True

    @staticmethod
    def _filter_service(vm_entry: VMEntry):
        """
        Filter function for service/system VMEntries. Returns VMs that
        have feature 'servicevm' set.
        """
        return vm_entry.service_vm


class AppPage:
    """
    Helper class for managing the entirety of Applications menu page.
    """
    def __init__(self, vm_manager: VMManager, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher):
        """
        :param vm_manager: VM Manager object
        :param builder: Gtk.Builder with loaded glade object
        :param desktop_file_manager: Desktop File Manager object
        """
        self.selected_vm_entry: Optional[VMRow] = None

        self.vm_list: Gtk.ListBox = builder.get_object('vm_list')
        self.app_list: Gtk.ListBox = builder.get_object('app_list')
        self.settings_list: Gtk.ListBox = builder.get_object('settings_list')
        self.vm_right_pane: Gtk.Box = builder.get_object('vm_right_pane')
        self.separator_top = builder.get_object('separator_top')
        self.separator_bottom = builder.get_object('separator_bottom')

        self.dispatcher = dispatcher

        self.dispatcher.add_handler(
            f'domain-feature-pre-set:{constants.FAVORITES_FEATURE}',
            self._update_fav_btns
        )

        self.network_indicator = NetworkIndicator()
        self.vm_right_pane.pack_start(self.network_indicator, False, False, 0)
        self.vm_right_pane.reorder_child(self.network_indicator, 0)


        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect('row-activated', self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        self.app_list.invalidate_sort()

        self.vm_entries: Dict[str, List[BaseAppEntry]] = {}

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

        desktop_file_manager.register_callback(self._app_info_callback)
        desktop_file_manager.register_callback(self._settings_callback)
        self.toggle_buttons = VMTypeToggle(builder)
        self.toggle_buttons.connect_to_toggle(self._button_toggled)

        vm_manager.register_new_vm_callback(self._vm_callback)
        # self.vm_list.set_sort_func(lambda x, y: x.sort_order > y.sort_order)
        self.vm_list.set_filter_func(self.toggle_buttons.filter_function)

        self.widget_order = [self.settings_list, self.app_list,
                             self.control_list]

    def _settings_callback(self, app_info):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        
        if 'X-XFCE-SettingsDialog' in app_info.categories and 'qubes' in app_info.entry_name:
            entry = BaseAppEntry(app_info)
            app_info.entries.append(entry)
            self.vm_list.add(entry)

    def _update_fav_btns(self, vm, event, feature, *_args, **_kwargs):
        """
        Update the favorite buttons in the app page
        """
        old_fav = _kwargs['oldvalue'].split(' ') if _kwargs['oldvalue'] else None
        new_fav = _kwargs['value'].split(' ')

        if old_fav and len(old_fav) > len(new_fav) or new_fav == ['']:
            remove_fav = set(old_fav) - set(new_fav)
            for entry in self.vm_entries[vm.name]:
                if entry.app_info.entry_name in remove_fav:
                    entry.update_fav_btns()
                    break


    def _app_info_callback(self, app_info):
        """
        Callback to be performed on all newly loaded ApplicationInfo instances.
        """
        if app_info.vm:          
            entry = BaseAppEntry(app_info)

            if app_info.vm.name not in self.vm_entries:
                self.vm_entries[app_info.vm.name] = [entry]
            else:
                self.vm_entries[app_info.vm.name].append(entry)

            app_info.entries.append(entry)
            self.app_list.add(entry)


    def _qubes_settings_callback(self, settings_entry):
        """
        Callback to be performed on all newly loaded qubes settings entries. 
        """
        if settings_entry:
            pass

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
        An somewhat hacky helper function that is used by keyboard navigation
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

    def _get_direction_child(self, widget: Gtk.ListBox,
                             direction: Gtk.DirectionType):
        """
        Find next widget in provided Gtk.DirectionType. Used when keyboard
        navigation fails.
        Due to problems in forcing Gtk.ListBox to return the rows that
        are currently shown, we re-use filter function _is_app_fitting
        to make sure a visible ListBoxRow is selected.
        """
        child_list = widget.get_children()
        if direction == Gtk.DirectionType.UP:
            child_list = reversed(child_list)
        for child in child_list:
            if widget != self.app_list or self._is_app_fitting(child):
                return child
        return widget.get_row_at_index(0)

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
        """
        Initialize own state. Optional parameter for selecting initially
        selected VM is currently not supported.
        """
        self.toggle_buttons.initialize_state()
        self.app_list.select_row(None)
        self._set_right_visibility(True)

    def _selection_changed(self, _widget, row: Optional[VMRow]):
        if row is None:
            self.selected_vm_entry = None
            self.app_list.ephemeral_vm = False
            self._set_right_visibility(False)
        elif isinstance(row, VMRow) and not row.vm_entry.service_vm:
            self.selected_vm_entry = row
            self._set_right_visibility(True)
            self.network_indicator.set_network_state(row.vm_entry.has_network)
            self.control_list.update_visibility(row.vm_entry.power_state)
            self.control_list.select_row(None)
            self.app_list.ephemeral_vm = bool(
                self.selected_vm_entry.vm_entry.parent_vm)
        elif isinstance(row, BaseAppEntry):
            row.run_app(None)
        self.app_list.invalidate_filter()

    def _set_right_visibility(self, visibility: bool):
        if not visibility:
            self.control_list.hide()
            self.settings_list.hide()
            self.network_indicator.set_visible(False)
            self.separator_top.hide()
            self.separator_bottom.hide()
        else:
            self.control_list.show_all()
            self.settings_list.show_all()
            self.separator_top.show_all()
            self.separator_bottom.show_all()
