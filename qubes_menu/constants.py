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
    "domain-pre-start": "Transient",
    "domain-start": "Running",
    "domain-start-failed": "Halted",
    "domain-paused": "Paused",
    "domain-unpaused": "Running",
    "domain-shutdown": "Halted",
    "domain-pre-shutdown": "Transient",
    "domain-shutdown-failed": "Running",
}

INITIAL_PAGE_FEATURE = "menu-initial-page"
SORT_RUNNING_FEATURE = "menu-sort-running"
POSITION_FEATURE = "menu-position"
DISABLE_RECENT_FEATURE = "menu-disable-recent"

FAVORITES_FEATURE = "menu-favorites"
FOLDER_FEATURE = "menu-folder"
FOLDER_FEATURE_APPS = "menu-folder-apps"
FOLDER_FEATURE_TEMPLATES = "menu-folder-templates"
FOLDER_FEATURE_SERVICE = "menu-folder-service"
FOLDERS_FEATURE = "menu-folders"
FOLDERS_COLLAPSED_FEATURE = "menu-folders-collapsed"
FOLDERS_FEATURE_APPS = "menu-folders-apps"
FOLDERS_FEATURE_TEMPLATES = "menu-folders-templates"
FOLDERS_FEATURE_SERVICE = "menu-folders-service"
FOLDERS_COLLAPSED_FEATURE_APPS = "menu-folders-collapsed-apps"
FOLDERS_COLLAPSED_FEATURE_TEMPLATES = "menu-folders-collapsed-templates"
FOLDERS_COLLAPSED_FEATURE_SERVICE = "menu-folders-collapsed-service"
DISPOSABLE_PREFIX = "@disp:"

RESTART_PARAM_LONG = "restart"
RESTART_PARAM_SHORT = "r"

# Timeout for activation change when hovering over a menu item, in microseconds
HOVER_TIMEOUT = 15
