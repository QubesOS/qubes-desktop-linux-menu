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
from qubesadmin.tests.mock_app import MockDispatcher
from ..search_page import SearchPage

def test_search(test_desktop_file_path, test_qapp, test_builder):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(DesktopFileManager, 'desktop_dirs',
                           [test_desktop_file_path]):
        desktop_file_manager = DesktopFileManager(test_qapp)

    search_page = SearchPage(vm_manager, test_builder, desktop_file_manager)

    assert search_page.search_entry.get_sensitive()

    # nothing should be visible
    assert len([row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]) == 0

    # try to find firefox
    search_page.search_entry.set_text('firefox')

    found_entries = [row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]
    assert len(found_entries) == 1
    assert found_entries[0].app_info.app_name == 'Firefox'

    search_page.search_entry.set_text('')

    # nothing should be visible
    assert len([row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]) == 0

    # check for no problems with caps
    search_page.search_entry.set_text('xTeRm')

    found_entries = [row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]
    assert len(found_entries) == 1
    assert found_entries[0].app_info.app_name == 'XTerm'

    search_page.search_entry.set_text('')

    # nothing should be visible
    assert len([row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]) == 0

    # try to use keywords in searching
    search_page.search_entry.set_text('dragons')

    found_entries = [row for row in search_page.app_list.get_children()
                     if search_page._is_app_fitting(row)]
    assert len(found_entries) == 1
    assert found_entries[0].app_info.app_name == 'Firefox'

    search_page.search_entry.set_text('')

    # nothing should be visible
    assert len([row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]) == 0

    # find a dom0 app
    search_page.search_entry.set_text('dom0')

    found_entries = [row for row in search_page.app_list.get_children()
                if search_page._is_app_fitting(row)]
    assert len(found_entries) == 1
    assert found_entries[0].app_info.app_name == 'Xfce Appearance Settings'

@mock.patch('gi.repository.Gtk.Application')
def test_recent_searches(mock_application, test_desktop_file_path, test_qapp,
                         test_builder):
    dispatcher = MockDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    with mock.patch.object(DesktopFileManager, 'desktop_dirs',
                           [test_desktop_file_path]):
        desktop_file_manager = DesktopFileManager(test_qapp)

    search_page = SearchPage(vm_manager, test_builder, desktop_file_manager)

    assert search_page.search_entry.get_sensitive()

    search_page.search_entry.set_text('dragons')

    # find a dom0 app
    search_page.search_entry.set_text('dom0')

    for row in search_page.app_list.get_children():
        if search_page._is_app_fitting(row):
            with mock.patch('subprocess.Popen') as mock_run, mock.patch.object(
                    row.get_toplevel(), 'get_application', side_effect=mock_application):
                row.activate()
                assert mock_run.call_count == 1
                assert mock.call().emit('app-started', 'test3.desktop') in mock_application.mock_calls

    # we are faking signals here
    search_page.recent_apps_manager.add_new_recent_app(None, 'test3.desktop')

    texts = [row.search_text for row in search_page.recent_list.get_children()]
    assert texts == ['dom0']
    apps = [row.app_info.entry_name for row in
            search_page.recent_app_list.get_children()]
    assert apps == ['test3.desktop']

    # do two more searches, but one should be the same as an existing search
    search_page.search_entry.set_text('')
    search_page.search_entry.set_text('xTeRm')

    for row in search_page.app_list.get_children():
        if search_page._is_app_fitting(row):
            with mock.patch('subprocess.Popen') as mock_run, mock.patch.object(
                    row.get_toplevel(), 'get_application', side_effect=mock_application):
                row.activate()
                assert mock_run.call_count == 1
                assert mock.call().emit('app-started', 'test1.desktop') in mock_application.mock_calls

    search_page.recent_apps_manager.add_new_recent_app(None, 'test1.desktop')
    search_page.search_entry.set_text('')
    search_page.search_entry.set_text('dom0')

    for row in search_page.app_list.get_children():
        if search_page._is_app_fitting(row):
            with mock.patch('subprocess.Popen') as mock_run, mock.patch.object(
                    row.get_toplevel(), 'get_application', side_effect=mock_application):
                row.activate()
                assert mock_run.call_count == 1
                assert mock.call().emit('app-started', 'test3.desktop') in mock_application.mock_calls

    search_page.recent_apps_manager.add_new_recent_app(None, 'test3.desktop')

    texts = [row.search_text for row in search_page.recent_list.get_children()]
    assert texts == ['dom0', 'xTeRm']
    apps = [row.app_info.entry_name for row in
            search_page.recent_app_list.get_children()]
    assert apps == ['test3.desktop', 'test1.desktop']
