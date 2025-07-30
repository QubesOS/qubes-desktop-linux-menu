# -*- encoding: utf8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2022 Marta Marczykowska-Górecka
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
"""Abstract Menu page"""
import abc

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class MenuPage(abc.ABC):
    """Abstract Menu Page."""

    page_widget: Gtk.Widget

    @abc.abstractmethod
    def initialize_page(self):
        """Perform all initial / post-switch configuration for the page. This
        will be called on start and whenever menu switches to the given page."""

    def set_sorting_order(self, sort_running: bool = False):
        """Set special sorting order options."""
