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
Qubes App Menu constants, like dictionary of events-to-vm-states, name of
favorites feature etc.
"""

STATE_DICTIONARY = {
    'domain-pre-start': 'Transient',
    'domain-start': 'Running',
    'domain-start-failed': 'Halted',
    'domain-paused': 'Paused',
    'domain-unpaused': 'Running',
    'domain-shutdown': 'Halted',
    'domain-pre-shutdown': 'Transient',
    'domain-shutdown-failed': 'Running'
}

FAVORITES_FEATURE = 'menu-favorites'
DISPOSABLE_PREFIX = '@disp:'

RESTART_PARAM_LONG = 'restart'
RESTART_PARAM_SHORT = 'r'

# Timeout for activation change when hovering over a menu item, in microseconds
HOVER_TIMEOUT = 20
