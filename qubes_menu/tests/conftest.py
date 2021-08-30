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
import unittest.mock
from qubesadmin.tests import TestVM, TestVMCollection


class TestApp(object):
    def __init__(self):
        self.domains = TestVMCollection(
            [
                ('dom0', TestVM('dom0')),
            ]
        )
        self.log = unittest.mock.Mock()

    def _invalidate_cache(self, *_args, **_kwargs):
        pass


@pytest.fixture
def test_qapp():
    app = TestApp()
    app.domains = TestVMCollection(
        [
            ('dom0', TestVM('dom0', label='black', icon='adminvm-black'
                            , features={})),
            ('test-vm',
             TestVM('test-vm', label='blue', icon='appvm-blue',
                    netvm=TestVM('sys-firewall'), template=TestVM('template'),
                    features={})),
            ('sys-firewall',
             TestVM('sys-firewall', label='green', icon='servicevm-green',
                    netvm=TestVM('sys-net'), template=TestVM('template'),
                    features={})),
            ('sys-net',
             TestVM('sys-net', label='red', icon='servicevm-red',
                    provides_network=True, template=TestVM('template'),
                    features={'servicevm': 1})),
            ('template',
             TestVM('template', label='red', icon='templatevm-red',
                    features={})),
            ('template-dvm',
             TestVM('template-dvm', label='red', icon='templatevm-red',
                    template_for_dispvms=True, netvm=TestVM('sys-net'),
                    template=TestVM('template'), features={})),
        ]
    )
    return app
