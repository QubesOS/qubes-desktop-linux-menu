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
from ..appmenu import AppMenu
from qubesadmin.tests.mock_app import MockQubesComplete, MockDispatcher, MockQube


def test_app_menu_conffeatures():
    qapp = MockQubesComplete()

    qapp._qubes['test-vm2'] = MockQube(name="test-vm2", qapp=qapp,
                                       features={'menu-favorites': ''})
    qapp._qubes['dom0'].features['menu-initial-page'] = 'favorites_page'
    qapp._qubes['dom0'].features['menu-sort-running'] = '1'
    qapp.update_vm_calls()

    dispatcher = MockDispatcher(qapp)
    app_menu = AppMenu(qapp, dispatcher)

    app_menu.perform_setup()

    # check that initial page is correct
    assert app_menu.initial_page == "favorites_page"
    assert app_menu.sort_running


def test_app_menu_conffeatures_default():
    qapp = MockQubesComplete()

    # make sure the features exist, but should not be shown
    qapp._qubes['test-vm2'] = MockQube(
        name="test-vm2", qapp=qapp,
        features={'menu-favorites': '',
                  'menu-initial-page': 'fake',
                  'menu-sort-running': 'fake'})
    qapp.update_vm_calls()

    dispatcher = MockDispatcher(qapp)
    app_menu = AppMenu(qapp, dispatcher)

    app_menu.perform_setup()

    # check that default configuration is correct
    assert app_menu.initial_page == "app_page"
    assert not app_menu.sort_running


def test_appmenu_options():
    qapp = MockQubesComplete()

    qapp._qubes['test-vm2'] = MockQube(name="test-vm2", qapp=qapp,
                                       features={'menu-favorites': ''})
    qapp._qubes['dom0'].features['menu-initial-page'] = 'app_page'
    qapp._qubes['dom0'].features['menu-sort-running'] = '1'
    qapp.update_vm_calls()

    dispatcher = MockDispatcher(qapp)
    app_menu = AppMenu(qapp, dispatcher)

    app_menu.perform_setup()

    assert app_menu.initial_page == "app_page"
    assert not app_menu.keep_visible
    options = {
        "keep-visible": True,
        "page": "2"
    }

    app_menu.parse_options(options)

    assert app_menu.initial_page == "favorites_page"
    assert app_menu.keep_visible
