# pylint: skip-file
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
from .menu_settings import AppMenuSettings
from qubesadmin.tests.mock_app import MockQubesComplete


def test_menu_settings_load():
    qapp = MockQubesComplete()
    qapp._qubes['dom0'].features['menu-initial-page'] = '2'
    qapp._qubes['dom0'].features['menu-sort-running'] = '1'
    qapp._qubes['dom0'].features['menu-favorites'] = ''

    qapp.update_vm_calls()

    app = AppMenuSettings(qapp)

    app.perform_setup()

    assert app.initial_page_model.get_selected() == 2
    assert app.sort_running_check.get_active()


def test_menu_settings_change():
    qapp = MockQubesComplete()
    qapp._qubes['dom0'].features['menu-initial-page'] = '1'
    qapp._qubes['dom0'].features['menu-sort-running'] = ''
    qapp._qubes['dom0'].features['menu-favorites'] = ''

    qapp.update_vm_calls()

    app = AppMenuSettings(qapp)

    app.perform_setup()

    assert app.initial_page_model.get_selected() == 1
    assert not app.sort_running_check.get_active()

    app.starting_page_combo.set_active_id("Search")  # the first option is search
    app.sort_running_check.set_active(True)

    qapp.expected_calls[('dom0', 'admin.vm.feature.Set', 'menu-sort-running', b'1')] = b'0\0'
    qapp.expected_calls[('dom0', 'admin.vm.feature.Set', 'menu-initial-page', b'0')] = b'0\0'

    app._save()


def test_menu_settings_change2():
    qapp = MockQubesComplete()
    qapp._qubes['dom0'].features['menu-initial-page'] = '1'
    qapp._qubes['dom0'].features['menu-sort-running'] = ''
    qapp._qubes['dom0'].features['menu-favorites'] = ''

    qapp.update_vm_calls()

    app = AppMenuSettings(qapp)

    app.perform_setup()

    assert app.initial_page_model.get_selected() == 1
    assert not app.sort_running_check.get_active()

    app.starting_page_combo.set_active_id("Favorites")

    qapp.expected_calls[('dom0', 'admin.vm.feature.Set', 'menu-initial-page', b'2')] = b'0\0'

    app._save()
