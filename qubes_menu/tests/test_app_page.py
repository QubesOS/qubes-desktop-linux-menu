# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2023 Marta Marczykowska-Górecka
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
from unittest import mock
import json

from ..desktop_file_manager import DesktopFileManager
from ..vm_manager import VMManager
from ..custom_widgets import FolderRow
from .. import constants
from qubesadmin.tests.mock_app import MockDispatcher, MockQube
from ..application_page import AppPage
from ..settings_page import SettingsPage


def test_app_page_vm_state(test_desktop_file_path, test_qapp, test_builder):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)

    # For some reason it defaults to the system tab.
    app_page.toggle_buttons.apps_toggle.set_active(True)

    # select dom0
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if row.vm_name == "dom0"
        ][0]
    )
    assert app_page.control_list.start_item.row_label.get_label() == " "
    assert app_page.control_list.pause_item.row_label.get_label() == " "

    # select a turned off vm
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if row.vm_name == "test-red"
        ][0]
    )

    assert (
        app_page.control_list.start_item.row_label.get_label() == "Start qube"
    )
    assert app_page.control_list.pause_item.row_label.get_label() == " "

    # select a turned on vm
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if row.vm_name == "sys-usb"
        ][0]
    )

    assert (
        app_page.control_list.start_item.row_label.get_label()
        == "Shutdown qube"
    )
    assert (
        app_page.control_list.pause_item.row_label.get_label() == "Pause qube"
    )

    # select a turned off disposable template
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if row.vm_name == "test-alt-dvm"
        ][0]
    )
    assert app_page.control_list.start_item.row_label.get_label() == " "
    assert app_page.control_list.pause_item.row_label.get_label() == " "

    # select a turned on disposable template
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if row.vm_name == "test-alt-dvm-running"
        ][0]
    )
    assert (
        app_page.control_list.start_item.row_label.get_label()
        == "Shutdown qube"
    )
    assert (
        app_page.control_list.pause_item.row_label.get_label() == "Pause qube"
    )


def test_dispvm_parent_sorting(test_desktop_file_path, test_qapp, test_builder):
    # check if dispvm child is sorted after the parent
    test_qapp._qubes["disp1233"] = MockQube(
        name="disp1233",
        qapp=test_qapp,
        klass="DispVM",
        template_for_dispvms="True",
        template="default-dvm",
        auto_cleanup=True,
    )
    test_qapp.update_vm_calls()

    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)

    found_dvm = False

    for row in app_page.vm_list.get_children():
        if found_dvm:
            if row.vm_name == "disp1233" and row.vm_entry.parent_vm:
                break
            found_dvm = False
            continue
        if row.vm_entry.is_dispvm_template:
            found_dvm = True
            continue
        found_dvm = False
    else:
        assert False


def test_settings_app_page(test_desktop_file_path, test_qapp, test_builder):
    # a basic sanity test
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    settings_page = SettingsPage(
        test_qapp, test_builder, desktop_file_manager, dispatcher
    )

    for row in settings_page.app_list.get_children():
        assert not row.app_info.vm


def test_folder_create_assign_rename_delete(
    test_desktop_file_path, test_qapp, test_builder
):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)
    app_page.toggle_buttons.apps_toggle.set_active(True)
    app_page._save_scope_state = mock.Mock()

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}

    app_page._create_folder("Work")
    assert "Work" in app_page.folder_order

    app_page._assign_folder(vm_entry, "Work")
    assert app_page._vm_folder(vm_entry) == "Work"
    assert json.loads(
        vm_entry.vm.features[constants.FOLDER_FEATURE]
    ) == {"apps": "Work"}

    app_page._rename_folder("Work", "Projects")
    assert "Work" not in app_page.folder_order
    assert "Projects" in app_page.folder_order
    assert app_page._vm_folder(vm_entry) == "Projects"
    assert json.loads(
        vm_entry.vm.features[constants.FOLDER_FEATURE]
    ) == {"apps": "Projects"}

    app_page._delete_folder("Projects")
    assert "Projects" not in app_page.folder_order
    assert app_page._vm_folder(vm_entry) == ""
    assert constants.FOLDER_FEATURE not in vm_entry.vm.features


def test_folder_move_and_collapsed_state_saved(
    test_desktop_file_path, test_qapp, test_builder
):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)
    app_page.toggle_buttons.apps_toggle.set_active(True)
    app_page._save_scope_state = mock.Mock()

    app_page._create_folder("A")
    app_page._create_folder("B")
    app_page._create_folder("C")
    assert app_page.folder_order == [app_page.UNGROUPED, "A", "B", "C"]

    app_page._move_folder(None, "B", -1)
    assert app_page.folder_order == [app_page.UNGROUPED, "B", "A", "C"]

    app_page._move_folder(None, "B", 1)
    assert app_page.folder_order == [app_page.UNGROUPED, "A", "B", "C"]

    folder_b = app_page.folder_rows["B"]
    assert isinstance(folder_b, FolderRow)
    assert "B" not in app_page.collapsed_folders

    app_page._toggle_folder(folder_b)
    assert "B" in app_page.collapsed_folders
    app_page._save_scope_state.assert_called()

    app_page._set_all_folders_collapsed(None, True)
    assert set(app_page.folder_order) == app_page.collapsed_folders

    app_page._set_all_folders_collapsed(None, False)
    assert app_page.collapsed_folders == set()


def test_folder_state_is_scope_specific(
    test_desktop_file_path, test_qapp, test_builder
):
    test_qapp._qubes["dom0"].features[
        constants.FOLDER_COLLAPSED_FEATURE
    ] = json.dumps(
        {
            "apps": {
                "folders": ["Ungrouped", "AppsOnly"],
                "collapsed": ["AppsOnly"],
            },
            "templates": {
                "folders": ["Ungrouped", "TplOnly"],
                "collapsed": [],
            },
            "service": {
                "folders": ["Ungrouped", "SvcOnly"],
                "collapsed": [],
            },
        }
    )
    test_qapp.update_vm_calls()

    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)

    app_page.toggle_buttons.apps_toggle.set_active(True)
    assert app_page.folder_order == ["Ungrouped", "AppsOnly"]
    assert app_page.collapsed_folders == {"AppsOnly"}

    app_page.toggle_buttons.templates_toggle.set_active(True)
    assert app_page.folder_order == ["Ungrouped", "TplOnly"]

    app_page.toggle_buttons.system_toggle.set_active(True)
    assert app_page.folder_order == ["Ungrouped", "SvcOnly"]


def test_folder_selection_menu_entries(
    test_desktop_file_path, test_qapp, test_builder
):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)
    app_page.toggle_buttons.apps_toggle.set_active(True)
    app_page._save_scope_state = mock.Mock()

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}

    app_page._create_folder("Work")
    app_page._create_folder("Personal")
    app_page._assign_folder(vm_entry, "Work")

    submenu = app_page._folder_selection_menu(vm_entry, include_remove=True)
    labels = [item.get_label() for item in submenu.get_children()]

    assert "Work" not in labels
    assert "Personal" in labels
    assert "Create new folder…" in labels
    assert "Remove from folder" in labels


def test_unknown_vm_folder_falls_back_to_ungrouped(
    test_desktop_file_path, test_qapp, test_builder
):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)
    app_page.toggle_buttons.apps_toggle.set_active(True)

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {
        constants.FOLDER_FEATURE: json.dumps({"apps": "MissingFolder"})
    }

    vm_row = app_page.vm_rows["test-red"]

    assert app_page._effective_vm_folder(vm_entry) == app_page.UNGROUPED
    assert app_page._is_row_visible(vm_row)
