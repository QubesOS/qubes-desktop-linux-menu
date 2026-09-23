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

import qubesadmin.exc

from ..desktop_file_manager import DesktopFileManager
from ..vm_manager import VMManager
from ..custom_widgets import FolderRow, VMRow, SelfAwareMenu
from .. import constants
from qubesadmin.tests.mock_app import MockDispatcher, MockQube
from ..application_page import AppPage
from ..settings_page import SettingsPage


def _build_app_page(test_desktop_file_path, test_qapp, test_builder):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)
    with mock.patch.object(
        DesktopFileManager, "desktop_dirs", [test_desktop_file_path]
    ):
        desktop_file_manager = DesktopFileManager(test_qapp)
    return AppPage(vm_manager, test_builder, desktop_file_manager), vm_manager


def _install_fake_save(app_page, test_qapp):
    """Mirror _save_folder_state into the mock feature store."""
    guivm_mock = test_qapp._qubes["dom0"]

    def fake_save():
        guivm_mock.features[constants.FOLDER_ORDER_FEATURE] = (
            AppPage._encode_folder_list(app_page.folder_order)
        )
        collapsed = [
            name
            for name in app_page.folder_order + [app_page.UNGROUPED]
            if name in app_page.collapsed_folders
        ]
        guivm_mock.features[constants.FOLDER_COLLAPSED_FEATURE] = (
            AppPage._encode_folder_list(collapsed)
        )
        guivm_mock.update_calls()

    app_page._save_folder_state = fake_save
    return guivm_mock


def _assign_folders(app_page, vm_manager, assignments):
    for vm_name, folder in assignments:
        vm_entry = vm_manager.load_vm_from_name(vm_name)
        assert vm_entry
        vm_entry.vm.features = {}
        app_page._assign_folder(None, vm_entry, folder)


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
            if isinstance(row, VMRow) and row.vm_name == "dom0"
        ][0]
    )
    assert app_page.control_list.start_item.row_label.get_label() == " "
    assert app_page.control_list.pause_item.row_label.get_label() == " "

    # select a turned off vm
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if isinstance(row, VMRow) and row.vm_name == "test-red"
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
            if isinstance(row, VMRow) and row.vm_name == "sys-usb"
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
            if isinstance(row, VMRow) and row.vm_name == "test-alt-dvm"
        ][0]
    )
    assert app_page.control_list.start_item.row_label.get_label() == " "
    assert app_page.control_list.pause_item.row_label.get_label() == " "

    # select a turned on disposable template
    app_page.vm_list.select_row(
        [
            row
            for row in app_page.vm_list.get_children()
            if isinstance(row, VMRow) and row.vm_name == "test-alt-dvm-running"
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
        features={constants.FOLDER_FEATURE: ""},
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
        if not isinstance(row, VMRow):
            continue
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
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    app_page._save_folder_state = mock.Mock()

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}

    app_page._assign_folder(None, vm_entry, "Work")
    assert "Work" in app_page.folder_order
    assert app_page._vm_folder(vm_entry) == "Work"
    assert vm_entry.vm.features[constants.FOLDER_FEATURE] == "Work"

    app_page._rename_folder("Work", "Projects")
    assert "Work" not in app_page.folder_order
    assert "Projects" in app_page.folder_order
    assert app_page._vm_folder(vm_entry) == "Projects"
    assert vm_entry.vm.features[constants.FOLDER_FEATURE] == "Projects"

    app_page._delete_folder("Projects")
    assert "Projects" not in app_page.folder_order
    assert app_page._vm_folder(vm_entry) == ""
    assert constants.FOLDER_FEATURE not in vm_entry.vm.features


def test_folder_move_and_collapsed_state_saved(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    guivm_mock = _install_fake_save(app_page, test_qapp)
    _assign_folders(
        app_page,
        vm_manager,
        [("test-red", "A"), ("sys-usb", "B"), ("test-vm", "C")],
    )

    assert app_page.folder_order == ["A", "B", "C"]
    assert guivm_mock.features[constants.FOLDER_ORDER_FEATURE] == "A B C"
    assert list(app_page.folder_rows)[-1] == app_page.UNGROUPED

    app_page._move_folder(None, "B", -1)
    assert app_page.folder_order == ["B", "A", "C"]
    assert guivm_mock.features[constants.FOLDER_ORDER_FEATURE] == "B A C"

    app_page._move_folder(None, "B", 1)
    assert app_page.folder_order == ["A", "B", "C"]

    folder_b = app_page.folder_rows["B"]
    assert isinstance(folder_b, FolderRow)
    assert not hasattr(folder_b, "vm_entry")
    assert not hasattr(folder_b, "vm_name")
    assert "B" not in app_page.collapsed_folders

    app_page._toggle_folder(folder_b)
    assert "B" in app_page.collapsed_folders
    assert guivm_mock.features[constants.FOLDER_COLLAPSED_FEATURE] == "B"

    app_page._set_all_folders_collapsed(None, True)
    assert set(app_page.folder_rows) == app_page.collapsed_folders

    app_page._set_all_folders_collapsed(None, False)
    assert app_page.collapsed_folders == set()


def test_ungrouped_is_fixed_last(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    guivm_mock = _install_fake_save(app_page, test_qapp)
    _assign_folders(
        app_page,
        vm_manager,
        [("test-red", "A"), ("sys-usb", "B"), ("test-vm", "C")],
    )

    assert app_page.folder_order == ["A", "B", "C"]
    assert list(app_page.folder_rows) == ["A", "B", "C", "Ungrouped"]

    app_page._move_folder(None, "A", 1)
    assert app_page.folder_order == ["B", "A", "C"]
    assert guivm_mock.features[constants.FOLDER_ORDER_FEATURE] == "B A C"

    app_page._move_folder(None, app_page.UNGROUPED, -1)
    assert app_page.folder_order == ["B", "A", "C"]
    assert list(app_page.folder_rows)[-1] == app_page.UNGROUPED


def test_folder_row_sync_is_deferred_while_popup_is_open(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    _install_fake_save(app_page, test_qapp)
    _assign_folders(app_page, vm_manager, [("test-red", "A")])
    old_row = app_page.folder_rows["A"]

    with mock.patch.object(SelfAwareMenu, "OPEN_MENUS", 1), mock.patch.object(
        SelfAwareMenu, "_CLOSE_CALLBACKS", []
    ), mock.patch("qubes_menu.custom_widgets.GLib.idle_add") as idle_add:
        app_page._delete_folder("A")
        assert app_page.folder_order == []
        assert app_page.folder_rows["A"] is old_row
        idle_add.assert_not_called()
        assert SelfAwareMenu._CLOSE_CALLBACKS == [app_page._sync_folder_rows]

        # A second refresh request must not queue another callback.
        app_page._sync_folder_rows()
        assert len(SelfAwareMenu._CLOSE_CALLBACKS) == 1

        SelfAwareMenu._remove_from_open()
        idle_add.assert_called_once_with(app_page._sync_folder_rows)
        assert SelfAwareMenu._CLOSE_CALLBACKS == []

        idle_add.call_args.args[0]()
        assert app_page.folder_rows == {}


def test_folder_delete_prompt_escapes_markup(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, _vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )

    with mock.patch(
        "qubes_menu.application_page.ask_question", return_value=None
    ) as question:
        app_page._prompt_delete_folder(None, "<Work & Play>")

    question.assert_called_once_with(
        app_page.page_widget,
        "Delete folder",
        "Delete folder '&lt;Work &amp; Play&gt;' and move all qubes "
        "to Ungrouped?",
    )


def test_folder_state_is_global_across_tabs(
    test_desktop_file_path, test_qapp, test_builder
):
    test_qapp._qubes["test-red"].features[constants.FOLDER_FEATURE] = "Work"
    test_qapp._qubes["dom0"].features[
        constants.FOLDER_ORDER_FEATURE
    ] = "Ungrouped Work"
    test_qapp._qubes["dom0"].features[
        constants.FOLDER_COLLAPSED_FEATURE
    ] = "Work"
    test_qapp.update_vm_calls()

    app_page, _vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    assert app_page.folder_order == ["Work"]
    assert app_page.collapsed_folders == {"Work"}

    with mock.patch.object(app_page, "_sync_folder_rows") as sync_rows:
        app_page.toggle_buttons.templates_toggle.set_active(True)
        app_page.toggle_buttons.system_toggle.set_active(True)
        sync_rows.assert_not_called()

    assert app_page.folder_order == ["Work"]
    assert app_page.collapsed_folders == {"Work"}


def test_folder_disappears_after_its_last_assignment_is_removed(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    app_page._save_folder_state = mock.Mock()

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}

    app_page._assign_folder(None, vm_entry, "Work")
    assert app_page.folder_order == ["Work"]
    assert list(app_page.folder_rows) == ["Work", app_page.UNGROUPED]

    app_page._assign_folder(None, vm_entry, "")
    assert app_page.folder_order == []
    assert app_page.folder_rows == {}
    assert app_page._vm_folder(vm_entry) == ""


def test_folder_selection_menu_entries(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    app_page._save_folder_state = mock.Mock()

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}
    app_page._assign_folder(None, vm_entry, "Work")

    other_entry = vm_manager.load_vm_from_name("sys-usb")
    assert other_entry
    other_entry.vm.features = {}
    app_page._assign_folder(None, other_entry, "Personal")

    submenu = app_page._folder_selection_menu(vm_entry, include_remove=True)
    labels = [item.get_label() for item in submenu.get_children()]

    assert "Work" not in labels
    assert "Personal" in labels
    assert "Ungrouped" not in labels
    assert "Create new folder…" in labels
    assert "Remove from folder" in labels


def test_restored_vm_recreates_folder_missing_from_saved_order(
    test_desktop_file_path, test_qapp, test_builder
):
    test_qapp._qubes["test-red"].features[constants.FOLDER_FEATURE] = "Restored"
    test_qapp._qubes["dom0"].features[constants.FOLDER_ORDER_FEATURE] = "Old"
    test_qapp.update_vm_calls()

    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry

    assert app_page.folder_order == ["Restored"]
    assert "Restored" in app_page.folder_rows
    assert app_page._effective_vm_folder(vm_entry) == "Restored"


def test_disposable_inherits_parent_folder(
    test_desktop_file_path, test_qapp, test_builder
):
    test_qapp._qubes["default-dvm"].features[constants.FOLDER_FEATURE] = "Work"
    test_qapp._qubes["disp-folder-test"] = MockQube(
        name="disp-folder-test",
        qapp=test_qapp,
        klass="DispVM",
        template="default-dvm",
        auto_cleanup=True,
        features={constants.FOLDER_FEATURE: ""},
    )
    test_qapp.update_vm_calls()

    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    disposable = vm_manager.load_vm_from_name("disp-folder-test")
    assert disposable
    assert disposable.folder == ""
    assert app_page._effective_vm_folder(disposable) == "Work"


def test_folder_assignment_permission_error_keeps_state(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    denied_features = mock.MagicMock()
    denied_features.__setitem__.side_effect = (
        qubesadmin.exc.QubesDaemonAccessError("denied")
    )
    vm_entry.vm.features = denied_features

    with mock.patch("qubes_menu.application_page.show_error") as error:
        app_page._assign_folder(None, vm_entry, "Work")

    assert vm_entry.folder == ""
    assert app_page.folder_order == []
    error.assert_called_once()


def test_interface_qube_permission_error_is_reported(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, _vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    denied_features = mock.MagicMock()
    denied_features.__setitem__.side_effect = (
        qubesadmin.exc.QubesDaemonAccessError("denied")
    )
    app_page.local_vm.features = denied_features

    with mock.patch("qubes_menu.application_page.show_error") as error:
        assert not app_page._save_folder_state()

    error.assert_called_once()


def test_external_folder_events_update_rows(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )

    vm_manager._update_domain_feature(
        "test-red",
        f"feature-set:{constants.FOLDER_FEATURE}",
        feature=constants.FOLDER_FEATURE,
        value="External",
    )
    assert app_page.folder_order == ["External"]
    assert "External" in app_page.folder_rows

    vm_manager._update_domain_feature(
        "test-red",
        f"feature-delete:{constants.FOLDER_FEATURE}",
        feature=constants.FOLDER_FEATURE,
    )
    assert app_page.folder_order == []
    assert app_page.folder_rows == {}


def test_vm_removal_cleans_up_folder(
    test_desktop_file_path, test_qapp, test_builder
):
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page._save_folder_state = mock.Mock()
    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}
    app_page._assign_folder(None, vm_entry, "Temporary")

    vm_manager._remove_domain(None, "domain-delete", "test-red")

    assert "test-red" not in app_page.vm_rows
    assert app_page.folder_order == []
    assert app_page.folder_rows == {}


def test_folder_list_roundtrip_with_space_and_backslash_in_names():
    """Folder names survive quoting and the previous escape format."""
    names = [
        "My Folder",
        "back\\slash",
        "space \\ and space",
        "plain",
        "Ungrouped",
    ]
    encoded = AppPage._encode_folder_list(names)
    assert AppPage._decode_folder_list(encoded) == names
    assert AppPage._decode_folder_list(r"a\\ b c") == ["a\\", "b", "c"]
    assert AppPage._decode_folder_list(r"a\ b c") == ["a b", "c"]


def test_folder_state_with_names_containing_spaces(
    test_desktop_file_path, test_qapp, test_builder
):
    """menu-folder-order keeps folders with spaces as single entries."""
    app_page, vm_manager = _build_app_page(
        test_desktop_file_path, test_qapp, test_builder
    )
    app_page.toggle_buttons.apps_toggle.set_active(True)
    guivm_mock = _install_fake_save(app_page, test_qapp)

    vm_entry = vm_manager.load_vm_from_name("test-red")
    assert vm_entry
    vm_entry.vm.features = {}
    app_page._assign_folder(None, vm_entry, "sys usb")

    assert app_page.folder_order == ["sys usb"]
    assert guivm_mock.features[constants.FOLDER_ORDER_FEATURE] == "'sys usb'"

    app_page._load_folder_state()
    assert app_page.folder_order == ["sys usb"]
