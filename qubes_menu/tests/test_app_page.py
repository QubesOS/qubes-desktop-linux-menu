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

from ..desktop_file_manager import DesktopFileManager
from ..vm_manager import VMManager
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


def test_app_page_rows_of_selected_vm(
    test_desktop_file_path, test_qapp, test_builder
):
    # only rows of the selected qube are in the list, other rows are kept
    # out of it (not just filtered out)
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)

    app_page = AppPage(vm_manager, test_builder, desktop_file_manager)
    app_page.toggle_buttons.apps_toggle.set_active(True)

    def select(vm_name):
        app_page.vm_list.select_row(
            [
                row
                for row in app_page.vm_list.get_children()
                if row.vm_name == vm_name
            ][0]
        )

    def listed_apps():
        return [
            (row.app_info.vm.name, row.app_info.app_name)
            for row in app_page.app_list.get_children()
        ]

    rows = {
        app_info.vm.name: row
        for app_info in desktop_file_manager.get_app_infos()
        for row in app_info.entries
        if app_info.vm
    }
    assert set(rows) == {"test-vm", "test-red"}
    assert not app_page.app_list.get_children()

    select("test-vm")
    assert listed_apps() == [("test-vm", "XTerm")]
    assert rows["test-red"].get_parent() is None

    select("test-red")
    assert listed_apps() == [("test-red", "Firefox")]
    assert rows["test-vm"].get_parent() is None

    app_page.vm_list.unselect_all()
    assert not app_page.app_list.get_children()

    # a new app is listed only if its qube is selected
    select("test-vm")
    new_file = test_desktop_file_path / "test4.desktop"
    new_file.write_text(
        (test_desktop_file_path / "test1.desktop")
        .read_text()
        .replace("XTerm", "UXTerm")
    )
    desktop_file_manager.load_file(new_file)
    assert sorted(listed_apps()) == [
        ("test-vm", "UXTerm"),
        ("test-vm", "XTerm"),
    ]

    # removing an app of a qube that is not selected (so out of the list)
    desktop_file_manager.remove_file(test_desktop_file_path / "test2.desktop")
    select("test-red")
    assert not app_page.app_list.get_children()


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
