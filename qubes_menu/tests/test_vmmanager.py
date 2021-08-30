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

import pytest
import qubesadmin
import qubesadmin.events
from qubesadmin.tests import TestVM
from qubesadmin.label import Label
from ..vm_manager import VMManager


@pytest.mark.asyncio
def test_vm_manager(test_qapp):
    dispatcher = qubesadmin.events.EventsDispatcher(test_qapp)
    vm_manager = VMManager(test_qapp, dispatcher)

    entry_test = vm_manager.load_vm_from_name('test-vm')
    assert entry_test
    assert entry_test.vm_name == 'test-vm'
    assert entry_test.vm_icon_name == 'appvm-blue'
    entry_template = vm_manager.load_vm_from_name('template')
    assert entry_template
    assert not entry_template.has_network
    assert not entry_test.is_dispvm_template
    assert not entry_test.service_vm

    test_qapp.domains['template'].netvm = TestVM('sys-firewall')
    vm_manager._update_domain_property('template',
                                       'property-set:netvm', name='netvm',
                                       newvalue='sys-firewall',
                                       oldvalue=None)
    assert entry_template.has_network

    test_qapp.domains['test-vm'].label = Label(test_qapp, 'red')
    test_qapp.domains['test-vm'].icon = 'appvm-red'
    vm_manager._update_domain_property('test-vm',
                                       'property-set:label', name='label',
                                       newvalue='red',
                                       oldvalue='blue')
    assert entry_test.vm_icon_name == 'appvm-red'

    test_qapp.domains['test-vm'].template_for_dispvms = True
    vm_manager._update_domain_property('test-vm',
                                       'property-set:template_for_dispvms',
                                       name='template_for_dispvms',
                                       newvalue=True)
    assert entry_test.is_dispvm_template

    test_qapp.domains['test-vm'].features['servicevm'] = 1
    vm_manager._update_domain_feature('test-vm',
                                      'feature-set:servicevm',
                                      feature='servicevm',
                                      value=1)
    assert entry_test.service_vm
