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

import json
from typing import Optional, Dict, List, Set

from .desktop_file_manager import DesktopFileManager
from .custom_widgets import (
    NetworkIndicator,
    VMRow,
    FolderRow,
    SelfAwareMenu,
    ControlList,
    KeynavController,
)
from .app_widgets import AppEntry, BaseAppEntry
from .vm_manager import VMEntry, VMManager
from .page_handler import MenuPage
from .utils import get_visible_child
from . import constants

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class VMTypeToggle:
    """
    A class controlling a set of radio buttons for toggling
    which VMs are shown.
    """

    def __init__(self, builder: Gtk.Builder):
        """
        :param builder: Gtk.Builder, containing loaded glade data
        """
        self.apps_toggle: Gtk.RadioButton = builder.get_object("apps_toggle")
        self.templates_toggle: Gtk.RadioButton = builder.get_object(
            "templates_toggle"
        )
        self.system_toggle: Gtk.RadioButton = builder.get_object(
            "system_toggle"
        )
        self.vm_list: Gtk.ListBox = builder.get_object("vm_list")
        self.app_list: Gtk.ListBox = builder.get_object("app_list")

        self.buttons = [
            self.apps_toggle,
            self.templates_toggle,
            self.system_toggle,
        ]

        for button in self.buttons:
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            button.set_can_focus(True)
            # the below is necessary to make sure keyboard navigation
            # behaves correctly
            button.connect("focus", self._activate_button)

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
                button.set_size_request(button.get_allocated_width() * 1.2, -1)

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
            button.connect("toggled", func)

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
        if vm_entry.vm_klass == "TemplateVM":
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

    UNGROUPED = "Ungrouped"
    SCOPES = ["apps", "templates", "service"]

    SCOPE_VM_FEATURE = {
        "apps": constants.FOLDER_FEATURE_APPS,
        "templates": constants.FOLDER_FEATURE_TEMPLATES,
        "service": constants.FOLDER_FEATURE_SERVICE,
    }
    SCOPE_FOLDERS_FEATURE = {
        "apps": constants.FOLDERS_FEATURE_APPS,
        "templates": constants.FOLDERS_FEATURE_TEMPLATES,
        "service": constants.FOLDERS_FEATURE_SERVICE,
    }
    SCOPE_COLLAPSED_FEATURE = {
        "apps": constants.FOLDERS_COLLAPSED_FEATURE_APPS,
        "templates": constants.FOLDERS_COLLAPSED_FEATURE_TEMPLATES,
        "service": constants.FOLDERS_COLLAPSED_FEATURE_SERVICE,
    }

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
        self.selected_vm_entry: Optional[VMRow] = None
        self.sort_running = False  # Sort running VMs to top
        self.desktop_file_manager = desktop_file_manager
        self.vm_manager = vm_manager
        self.local_vm = self.vm_manager.qapp.domains[
            self.vm_manager.qapp.local_name
        ]
        self.vm_rows: Dict[str, VMRow] = {}
        self.folder_rows: Dict[str, FolderRow] = {}
        self.scope_folder_order: Dict[str, List[str]] = {
            scope: [] for scope in self.SCOPES
        }
        self.scope_collapsed_folders: Dict[str, Set[str]] = {
            scope: set() for scope in self.SCOPES
        }
        self.folder_order: List[str] = []
        self.collapsed_folders: Set[str] = set()
        self._load_folder_state_all()

        self.page_widget: Gtk.Box = builder.get_object("app_page")

        self.vm_list: Gtk.ListBox = builder.get_object("vm_list")
        self.app_list: Gtk.ListBox = builder.get_object("app_list")
        self.vm_right_pane: Gtk.Box = builder.get_object("vm_right_pane")
        self.separator_bottom = builder.get_object("separator_bottom")

        self.network_indicator = NetworkIndicator()
        self.vm_right_pane.pack_start(self.network_indicator, False, False, 0)
        self.vm_right_pane.reorder_child(self.network_indicator, 0)

        desktop_file_manager.register_callback(self._app_info_callback)
        self.toggle_buttons = VMTypeToggle(builder)
        self._activate_scope_state()
        self.toggle_buttons.connect_to_toggle(self._button_toggled)

        self.app_list.set_filter_func(self._is_app_fitting)
        self.app_list.connect("row-activated", self._app_clicked)
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.sort_name > y.app_info.sort_name
        )
        self.app_list.invalidate_sort()

        vm_manager.register_new_vm_callback(self._vm_callback)
        self.vm_list.set_sort_func(self._sort_vms)
        self.vm_list.set_filter_func(self._is_row_visible)

        self.vm_list.connect("row-selected", self._selection_changed)

        self.control_list = ControlList(self)
        self.control_list.connect("row-activated", self._app_clicked)
        self.vm_right_pane.pack_end(self.control_list, False, False, 0)

        self.setup_keynav()

        self.app_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.control_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.keynav_manager = KeynavController(
            widgets_in_order=[self.app_list, self.control_list]
        )

        self.widget_order = [self.app_list, self.control_list]

        self.vm_list.select_row(None)
        self._selection_changed(None, None)

        self.vm_list.connect("map", self._on_map_vm_list)
        self._rebuild_vm_rows_from_manager()
        self._rebuild_folder_rows()

    def _on_map_vm_list(self, *_args):
        # workaround for https://gitlab.gnome.org/GNOME/gtk/-/issues/4977
        # doesn't always fix it on the first try, but improves behavior in
        # case of unexpected focus chain changes, like pgup in some cases
        self.vm_list.select_row(self.vm_list.get_row_at_y(0))
        self.app_list.set_filter_func(None)
        self.app_list.invalidate_filter()
        self.app_list.set_filter_func(self._is_app_fitting)

        focus_child = get_visible_child(self.vm_list)
        focus_child.grab_focus()

    def _row_sort_key(self, row):
        if isinstance(row, FolderRow):
            return row.sort_order

        if not isinstance(row, VMRow):
            return "~"

        folder_name = self._effective_vm_folder(row.vm_entry)
        folder_index = self._folder_index(folder_name)

        state_prefix = "1"
        if self.sort_running and row.vm_entry.power_state == "Running":
            state_prefix = "0"

        return f"{folder_index:03d}:1:{state_prefix}:{row.sort_order}"

    def _sort_vms(self, first_row, second_row):
        return self._row_sort_key(first_row) > self._row_sort_key(second_row)

    def _folder_index(self, folder_name: str) -> int:
        if folder_name in self.folder_order:
            return self.folder_order.index(folder_name)
        return len(self.folder_order) + 1

    def _current_scope(self) -> str:
        if self.toggle_buttons.templates_toggle.get_active():
            return "templates"
        if self.toggle_buttons.system_toggle.get_active():
            return "service"
        return "apps"

    def _activate_scope_state(self):
        scope = self._current_scope()
        self.folder_order = self.scope_folder_order[scope].copy()
        self.collapsed_folders = self.scope_collapsed_folders[scope].copy()
        if self.UNGROUPED not in self.folder_order:
            self.folder_order.insert(0, self.UNGROUPED)

    def _vm_folder(self, vm_entry: VMEntry, scope: Optional[str] = None) -> str:
        if not scope:
            scope = self._current_scope()
        feature_name = self.SCOPE_VM_FEATURE[scope]
        return self._safe_feature_get(vm_entry.vm, feature_name, "")

    def _effective_vm_folder(
        self, vm_entry: VMEntry, scope: Optional[str] = None
    ) -> str:
        """Resolve VM folder name to an existing folder in current scope.

        Unknown/missing folder names are treated as Ungrouped to avoid
        orphaned rows when folder metadata and folder list are temporarily out
        of sync.
        """
        folder_name = self._vm_folder(vm_entry, scope)
        if not folder_name:
            return self.UNGROUPED
        if folder_name not in self.folder_order:
            return self.UNGROUPED
        return folder_name

    @staticmethod
    def _safe_feature_get(vm, feature_name: str, default=""):
        try:
            return str(vm.features.get(feature_name, default)).strip()
        except Exception:  # pylint: disable=broad-except
            return str(default).strip()

    def set_sorting_order(self, sort_running: bool = False):
        self.sort_running = sort_running
        for child in self.vm_list.get_children():
            if isinstance(child, VMRow):
                child.show_dispvm_inheritance = not self.sort_running
                child.update_style(False)
        self.vm_list.invalidate_sort()

    def setup_keynav(self):
        """Do all the required faffing about to convince Gtk to have
        reasonable keyboard nav"""
        self.vm_list.connect("keynav-failed", self._vm_keynav_failed)

        self.app_list.connect("key-press-event", self._focus_vm_list)
        self.control_list.connect("key-press-event", self._focus_vm_list)

        self.vm_list.connect("key-press-event", self._vm_key_pressed)

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
        if vm_entry and vm_entry.vm_name not in self.vm_rows:
            vm_row = VMRow(
                vm_entry,
                show_dispvm_inheritance=not self.sort_running,
                folder_menu_handler=self._show_vm_folder_menu,
            )
            vm_row.show_all()
            self.vm_rows[vm_entry.vm_name] = vm_row
            vm_entry.entries.append(vm_row)
            self.vm_list.add(vm_row)
            self._rebuild_folder_rows()
            self.vm_list.invalidate_filter()
            self.vm_list.invalidate_sort()

    def _rebuild_vm_rows_from_manager(self):
        selected = self.vm_list.get_selected_row()
        selected_name = getattr(selected, "vm_name", None)

        for child in list(self.vm_list.get_children()):
            if isinstance(child, VMRow):
                if child.vm_entry and child in child.vm_entry.entries:
                    child.vm_entry.entries.remove(child)
                self.vm_list.remove(child)

        self.vm_rows = {}

        for vm_entry in self.vm_manager.vms.values():
            vm_row = VMRow(
                vm_entry,
                show_dispvm_inheritance=not self.sort_running,
                folder_menu_handler=self._show_vm_folder_menu,
            )
            vm_row.show_all()
            self.vm_rows[vm_entry.vm_name] = vm_row
            vm_entry.entries.append(vm_row)
            self.vm_list.add(vm_row)

        self._rebuild_folder_rows()
        self.vm_list.invalidate_filter()
        self.vm_list.invalidate_sort()

        if selected_name:
            if selected_name in self.vm_rows:
                self.vm_list.select_row(self.vm_rows[selected_name])
            elif selected_name in self.folder_rows:
                self.vm_list.select_row(self.folder_rows[selected_name])

    def _show_vm_folder_menu(self, row: VMRow, event):
        if event.button != 3:
            return

        self.vm_list.select_row(row)

        menu = SelfAwareMenu()

        move_to_folder = Gtk.MenuItem(label="Move to folder")
        move_to_folder.set_submenu(
            self._folder_selection_menu(row.vm_entry, include_remove=False)
        )
        menu.add(move_to_folder)

        menu.show_all()
        menu.popup_at_pointer(None)

    def _folder_selection_menu(self, vm_entry: VMEntry, include_remove: bool):
        submenu = SelfAwareMenu()
        current_folder = self._vm_folder(vm_entry) or self.UNGROUPED

        for folder_name in self.folder_order:
            if folder_name == current_folder:
                continue
            item = Gtk.MenuItem(label=folder_name)
            item.connect(
                "activate", self._assign_folder_to_vm, vm_entry, folder_name
            )
            submenu.add(item)

        create_item = Gtk.MenuItem(label="Create new folder…")
        create_item.connect("activate", self._create_folder_for_vm, vm_entry)
        submenu.add(create_item)

        if include_remove:
            remove_item = Gtk.MenuItem(label="Remove from folder")
            remove_item.connect(
                "activate", self._assign_folder_to_vm, vm_entry, ""
            )
            submenu.add(remove_item)

        submenu.show_all()
        return submenu

    def _create_folder_for_vm(self, _widget, vm_entry: VMEntry):
        folder_name = self._prompt_for_text("Create folder")
        if folder_name is None:
            return
        folder_name = folder_name.strip()
        if not folder_name:
            return
        self._assign_folder(vm_entry, folder_name)

    def _assign_folder_to_vm(
        self, _widget, vm_entry: VMEntry, folder_name: str
    ):
        self._assign_folder(vm_entry, folder_name)

    def _rename_folder_from_row(self, _widget, row: VMRow):
        old_name = self._vm_folder(row.vm_entry)
        if not old_name:
            return

        new_name = self._prompt_for_text(
            title=f"Rename folder '{old_name}'",
            initial_value=old_name,
        )
        if new_name is None:
            return
        self._rename_folder(old_name, new_name)

    def _delete_folder_from_row(self, _widget, row: VMRow):
        folder = self._vm_folder(row.vm_entry)
        if not folder:
            return

        if not self._confirm(
            title="Delete folder",
            text=f"Delete folder '{folder}' and move all qubes to Ungrouped?",
        ):
            return
        self._delete_folder(folder)

    def _assign_folder(self, vm_entry: VMEntry, folder_name: str):
        folder_name = folder_name.strip()
        feature_name = self.SCOPE_VM_FEATURE[self._current_scope()]
        folder_added = False
        if folder_name:
            folder_added = folder_name not in self.folder_order
            self._ensure_folder_exists(folder_name)
            vm_entry.vm.features[feature_name] = folder_name
        else:
            try:
                del vm_entry.vm.features[feature_name]
            except KeyError:
                pass
        if folder_added:
            self._save_folder_state()
            self._rebuild_folder_rows()
        self.vm_list.invalidate_sort()
        self.vm_list.invalidate_filter()

    def _rename_folder(self, old_name: str, new_name: str):
        new_name = new_name.strip()
        if old_name == new_name:
            return
        if not old_name:
            return

        if old_name in self.folder_order:
            old_index = self.folder_order.index(old_name)
            if new_name and new_name not in self.folder_order:
                self.folder_order[old_index] = new_name
            else:
                del self.folder_order[old_index]

        if old_name in self.collapsed_folders:
            self.collapsed_folders.remove(old_name)
            if new_name:
                self.collapsed_folders.add(new_name)

        for vm_entry in self.vm_manager.vms.values():
            if self._vm_folder(vm_entry) != old_name:
                continue
            if new_name:
                feature_name = self.SCOPE_VM_FEATURE[self._current_scope()]
                vm_entry.vm.features[feature_name] = new_name
            else:
                try:
                    feature_name = self.SCOPE_VM_FEATURE[self._current_scope()]
                    del vm_entry.vm.features[feature_name]
                except KeyError:
                    pass

        self._save_folder_state()
        self._save_collapsed_state()
        self._rebuild_folder_rows()
        self.vm_list.invalidate_filter()
        self.vm_list.invalidate_sort()

    def _delete_folder(self, folder_name: str):
        if folder_name in self.folder_order:
            self.folder_order.remove(folder_name)
        self.collapsed_folders.discard(folder_name)

        for vm_entry in self.vm_manager.vms.values():
            if self._vm_folder(vm_entry) != folder_name:
                continue
            try:
                feature_name = self.SCOPE_VM_FEATURE[self._current_scope()]
                del vm_entry.vm.features[feature_name]
            except KeyError:
                pass

        self._save_folder_state()
        self._save_collapsed_state()
        self._rebuild_folder_rows()
        self.vm_list.invalidate_filter()
        self.vm_list.invalidate_sort()

    def _create_folder(self, folder_name: str):
        folder_name = folder_name.strip()
        if not folder_name:
            return
        self._ensure_folder_exists(folder_name)
        self._save_folder_state()
        self._rebuild_folder_rows()
        self.vm_list.invalidate_filter()
        self.vm_list.invalidate_sort()

    def _ensure_folder_exists(self, folder_name: str):
        folder_name = folder_name.strip()
        if not folder_name:
            return
        if folder_name in self.folder_order:
            return
        self.folder_order.append(folder_name)

    def _toggle_folder(self, folder_row: FolderRow):
        if folder_row.folder_name in self.collapsed_folders:
            self.collapsed_folders.remove(folder_row.folder_name)
            folder_row.collapsed = False
        else:
            self.collapsed_folders.add(folder_row.folder_name)
            folder_row.collapsed = True

        folder_row.update_contents()
        self._save_collapsed_state()
        self.vm_list.invalidate_filter()

    def _show_folder_row_menu(self, row: FolderRow, event):
        if event.button != 3:
            return

        menu = SelfAwareMenu()

        if row.folder_name != self.UNGROUPED:
            rename_folder = Gtk.MenuItem(label="Rename folder…")
            rename_folder.connect(
                "activate", self._rename_folder_from_folder_row, row
            )
            menu.add(rename_folder)

            delete_folder = Gtk.MenuItem(label="Delete folder")
            delete_folder.connect(
                "activate", self._delete_folder_from_folder_row, row
            )
            menu.add(delete_folder)

        move_up = Gtk.MenuItem(label="Move folder up")
        move_up.connect("activate", self._move_folder, row.folder_name, -1)
        menu.add(move_up)

        move_down = Gtk.MenuItem(label="Move folder down")
        move_down.connect("activate", self._move_folder, row.folder_name, 1)
        menu.add(move_down)

        collapse_all = Gtk.MenuItem(label="Collapse all")
        collapse_all.connect("activate", self._set_all_folders_collapsed, True)
        menu.add(collapse_all)

        expand_all = Gtk.MenuItem(label="Expand all")
        expand_all.connect("activate", self._set_all_folders_collapsed, False)
        menu.add(expand_all)

        menu.show_all()
        menu.popup_at_pointer(None)

    def _rename_folder_from_folder_row(self, _widget, row: FolderRow):
        old_name = row.folder_name
        new_name = self._prompt_for_text(
            title=f"Rename folder '{old_name}'",
            initial_value=old_name,
        )
        if new_name is None:
            return
        self._rename_folder(old_name, new_name)

    def _delete_folder_from_folder_row(self, _widget, row: FolderRow):
        folder = row.folder_name
        if not self._confirm(
            title="Delete folder",
            text=f"Delete folder '{folder}' and move all qubes to Ungrouped?",
        ):
            return
        self._delete_folder(folder)

    def _move_folder(self, _widget, folder_name: str, direction: int):
        if folder_name not in self.folder_order:
            return
        old_index = self.folder_order.index(folder_name)
        new_index = old_index + direction
        if new_index < 0 or new_index >= len(self.folder_order):
            return
        self.folder_order.insert(new_index, self.folder_order.pop(old_index))
        self._save_folder_state()
        self._rebuild_folder_rows()
        self.vm_list.invalidate_sort()

    def _set_all_folders_collapsed(self, _widget, collapsed: bool):
        # mutate in place to preserve per-scope set references
        self.collapsed_folders.clear()
        if collapsed:
            self.collapsed_folders.update(self.folder_order)

        for _folder_name, folder_row in self.folder_rows.items():
            folder_row.collapsed = collapsed
            folder_row.update_contents()

        self._save_collapsed_state()
        self.vm_list.invalidate_filter()

    def _load_folder_state_all(self):
        for scope in self.SCOPES:
            try:
                raw_folders = self.local_vm.features.get(
                    self.SCOPE_FOLDERS_FEATURE[scope], "[]"
                )
            except Exception:  # pylint: disable=broad-except
                raw_folders = "[]"
            try:
                raw_collapsed = self.local_vm.features.get(
                    self.SCOPE_COLLAPSED_FEATURE[scope], "[]"
                )
            except Exception:  # pylint: disable=broad-except
                raw_collapsed = "[]"

            try:
                parsed_folders = json.loads(raw_folders)
            except (TypeError, json.JSONDecodeError):
                parsed_folders = []

            try:
                parsed_collapsed = json.loads(raw_collapsed)
            except (TypeError, json.JSONDecodeError):
                parsed_collapsed = []

            folders = [f for f in parsed_folders if isinstance(f, str) and f]
            if self.UNGROUPED not in folders:
                folders.insert(0, self.UNGROUPED)
            allowed_collapsed = set(folders)
            allowed_collapsed.add(self.UNGROUPED)
            collapsed = {
                f
                for f in parsed_collapsed
                if isinstance(f, str) and f in allowed_collapsed
            }

            self.scope_folder_order[scope] = folders
            self.scope_collapsed_folders[scope] = collapsed

    def _save_folder_state(self):
        feature_name = self.SCOPE_FOLDERS_FEATURE[self._current_scope()]
        self.local_vm.features[feature_name] = json.dumps(self.folder_order)

    def _save_collapsed_state(self):
        collapsed = [
            f for f in self.folder_order if f in self.collapsed_folders
        ]
        self.local_vm.features[
            self.SCOPE_COLLAPSED_FEATURE[self._current_scope()]
        ] = json.dumps(collapsed)

    def _rebuild_folder_rows(self):
        for child in list(self.vm_list.get_children()):
            if isinstance(child, FolderRow):
                self.vm_list.remove(child)

        self.folder_rows = {}
        folders = self.folder_order

        # If only Ungrouped exists, don't show any folder headers at all;
        # display VMs flat instead.
        real_folders = [f for f in folders if f != self.UNGROUPED]
        if not real_folders:
            self.collapsed_folders.discard(self.UNGROUPED)
            self.vm_list.invalidate_sort()
            self.vm_list.invalidate_filter()
            return

        for idx, folder_name in enumerate(folders):
            row = FolderRow(
                folder_name=folder_name,
                collapsed=folder_name in self.collapsed_folders,
                toggle_handler=self._toggle_folder,
                menu_handler=self._show_folder_row_menu,
            )
            row.sort_order = f"{idx:03d}:0:{folder_name.lower()}"
            self.folder_rows[folder_name] = row
            self.vm_list.add(row)
            row.show_all()

        self.vm_list.invalidate_sort()
        self.vm_list.invalidate_filter()

    def _folder_has_visible_vms(self, folder_name: str):
        for row in self.vm_rows.values():
            vm_folder = self._effective_vm_folder(row.vm_entry)
            if vm_folder != folder_name:
                continue
            if self.toggle_buttons.filter_function(row):
                return True
        return False

    def _is_row_visible(self, row):
        if isinstance(row, FolderRow):
            return self._folder_has_visible_vms(row.folder_name)

        if not isinstance(row, VMRow):
            return False

        vm_folder = self._effective_vm_folder(row.vm_entry)
        if not self.toggle_buttons.filter_function(row):
            return False
        if vm_folder in self.collapsed_folders:
            return False
        return True

    def _prompt_for_text(self, title: str, initial_value: str = ""):
        dialog = Gtk.Dialog(
            title=title,
            transient_for=self.page_widget.get_toplevel(),
            modal=True,
        )
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        entry.set_text(initial_value)
        content.pack_start(entry, True, True, 8)
        dialog.set_default_response(Gtk.ResponseType.OK)

        dialog.show_all()
        response = dialog.run()
        text = entry.get_text()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return None
        return text

    def _confirm(self, title: str, text: str) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.page_widget.get_toplevel(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=text,
        )
        dialog.set_title(title)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _is_app_fitting(self, appentry: BaseAppEntry):
        """
        Filter function for applications - attempts to filter only
        applications that have a VM same as selected VM, or, in the case
        of disposable VMs that are children of a parent DVM template,
        show the DVM's menu entries.
        """
        if not self.selected_vm_entry:
            return False
        if (
            appentry.app_info.vm
            and appentry.app_info.vm.name
            != self.selected_vm_entry.vm_entry.vm_name
        ):
            return (
                self.selected_vm_entry.vm_entry.parent_vm
                == appentry.app_info.vm.name
                and not appentry.app_info.disposable
            )
        if self.selected_vm_entry.vm_entry.is_dispvm_template:
            return (
                appentry.app_info.disposable
                == self.toggle_buttons.apps_toggle.get_active()
            )
        return True

    def _vm_keynav_failed(self, _widget, direction: Gtk.DirectionType):
        if direction == Gtk.DirectionType.UP:
            self.toggle_buttons.grab_focus()

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
        self._activate_scope_state()
        self._rebuild_folder_rows()
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
        if row is None or not isinstance(row, VMRow):
            self.vm_list.unselect_all()
            self.selected_vm_entry = None
            self.app_list.ephemeral_vm = False
            self._set_right_visibility(False)
        else:
            self.selected_vm_entry = row
            self._set_right_visibility(True)
            self.network_indicator.set_network_state(row.vm_entry.has_network)
            self.control_list.update_visibility(
                row.vm_entry, self.toggle_buttons.apps_toggle.get_active()
            )
            self.control_list.unselect_all()
            self.app_list.ephemeral_vm = bool(
                self.selected_vm_entry.vm_entry.parent_vm
            )
        self.app_list.invalidate_filter()

    def _set_right_visibility(self, visibility: bool):
        self.vm_right_pane.set_visible(visibility)
        self.control_list.set_visible(visibility)
        self.app_list.set_visible(visibility)
        self.separator_bottom.set_visible(visibility)
        if not visibility:
            self.network_indicator.set_visible(False)

    def get_selected_vm(self) -> Optional[VMEntry]:
        """Get currently selected vm"""
        if self.selected_vm_entry:
            return self.selected_vm_entry.vm_entry
        return None
