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

import os

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

RUNNING   = 'Running'
HALTED    = 'Halted'
TRANSIENT = 'Transient'
PAUSED    = 'Paused'

FAVORITES_FEATURE = 'menu-favorites'
DISPOSABLE_PREFIX = '@disp:'

RESTART_PARAM_LONG = 'restart'
RESTART_PARAM_SHORT = 'r'

# Timeout for activation change when hovering over a menu item, in microseconds
HOVER_TIMEOUT = 0

SETTINGS_PATH = os.path.join(os.getenv('HOME'), '.config/qappmenu-settings.ini')

FAVORITE_APPS_LAYOUT = 'favoriteappslayout'
SETTINGS = 'Settings'
LIST = 'list'
GRID = 'grid'

LIGHT_MODE = 'lightmode'
DARK = 'dark'
LIGHT = 'light'

# Icons
BOOKMARK_BLACK = "/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-black.svg"
BOOKMARK_FILL_BLACK = "/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-fill-black.svg"

BOOKMARK_FILL_WHITE = "/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-fill-white.svg"
BOOKMARK_WHITE = "/usr/share/icons/hicolor/scalable/apps/qappmenu-bookmark-white.svg"

LIST_WHITE = "/usr/share/icons/hicolor/scalable/apps/qappmenu-list-white.svg"
LIST_BLACK = "/usr/share/icons/hicolor/scalable/apps/qappmenu-list-black.svg"

GRID_WHITE = "/usr/share/icons/hicolor/scalable/apps/qappmenu-grid-white.svg"
GRID_BLACK = "/usr/share/icons/hicolor/scalable/apps/qappmenu-grid-black.svg"

SUN_WHITE = "/usr/share/icons/hicolor/scalable/apps/qappmenu-sun-white.svg"
SUN_BLACK = "/usr/share/icons/hicolor/scalable/apps/qappmenu-sun-black.svg"

MOON_WHITE = "/usr/share/icons/hicolor/scalable/apps/qappmenu-moon-white.svg"
MOON_BLACK = "/usr/share/icons/hicolor/scalable/apps/qappmenu-moon-black.svg"