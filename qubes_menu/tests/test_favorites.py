# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2020 Marta Marczykowska-Górecka
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

from ..app_widgets import BaseAppEntry, FavoritesAppEntry
from ..desktop_file_manager import ApplicationInfo
from unittest.mock import Mock, patch


def test_add_to_favorites(tmp_path, test_qapp):
    app_info = ApplicationInfo(test_qapp, tmp_path)
    vm = test_qapp.domains['test-vm']
    app_info.vm = vm
    app_info.app_name = 'Test App'
    app_info.entry_name = 'org.test.app'
    app_info.app_icon = None
    app_info.vm_icon = None

    base_entry = BaseAppEntry(app_info)
    base_entry._add_to_favorites()

    assert vm.features.get('menu-favorites') == 'org.test.app'

    base_entry._add_to_favorites()
    base_entry._add_to_favorites()

    assert vm.features.get('menu-favorites') == 'org.test.app'

    mock_manager = Mock()

    fav_entry = FavoritesAppEntry(app_info, mock_manager)
    fav_entry._remove_from_favorites()
    assert vm.features.get('menu-favorites') == ''
    base_entry._add_to_favorites()
    assert vm.features.get('menu-favorites') == 'org.test.app'

    second_app_info = ApplicationInfo(test_qapp, tmp_path)
    second_app_info.vm = vm
    second_app_info.app_name = 'Second App'
    second_app_info.entry_name = 'org.second.app'
    second_app_info.app_icon = None
    second_app_info.vm_icon = None

    second_base_entry = BaseAppEntry(second_app_info)
    second_fav_entry = FavoritesAppEntry(second_app_info, mock_manager)

    with patch.object(second_fav_entry, 'get_parent'):
        second_fav_entry._remove_from_favorites()
    assert vm.features.get('menu-favorites') == 'org.test.app'
    second_base_entry._add_to_favorites()
    assert vm.features.get('menu-favorites') == 'org.test.app org.second.app'
    second_fav_entry._remove_from_favorites()
    assert vm.features.get('menu-favorites') == 'org.test.app'
    second_base_entry._add_to_favorites()
    fav_entry._remove_from_favorites()
    assert vm.features.get('menu-favorites') == 'org.second.app'
