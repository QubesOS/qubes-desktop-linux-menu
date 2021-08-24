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
A collection of custom Gtk widgets used elsewhere in the App Menu
"""
import subprocess
import logging

from .custom_widgets import LimitedWidthLabel, SelfAwareMenu
from .desktop_file_manager import ApplicationInfo
from .utils import load_icon
from . import constants

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


logger = logging.getLogger('qubes-appmenu')


class AppEntry(Gtk.ListBoxRow):
    """
    Basic Application ListBoxRow entry, designed to be used as a base
    class:
    - supports a right-click menu that keeps track whether its open or not
    - supports an update_contents method for updating when changes in
    related desktop file are noticed
    - supports running an application on click; after click signals to the
    complete menu it might need hiding
    """
    def __init__(self, app_info: ApplicationInfo, **properties):
        """
        :param app_info: ApplicationInfo obj with data about related app file
        :param properties: additional Gtk.ListBoxRow properties
        """
        super().__init__(**properties)
        self.app_info = app_info

        self.menu = SelfAwareMenu()

        self.event_box = Gtk.EventBox()
        self.add(self.event_box)
        self.event_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.event_box.connect('button-press-event', self.show_menu)

    def show_menu(self, _widget, event):
        """
        Display own right click menu.
        """
        if event.button == 3:
            self.menu.popup_at_pointer(None)  # None means current event

    def update_contents(self):
        """
        Update any contents. To be called on changes in related .desktop
        file.
        """

    def run_app(self, vm):
        """
        Run application from related .desktop file for a given VM.
        :param vm: QubesVM
        """
        command = self.app_info.get_command_for_vm(vm)
        subprocess.Popen(command, stdout=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_toplevel().get_application().hide_menu()


class BaseAppEntry(AppEntry):
    """
    A 'normal' Application row, used by main applications menu and system tools.
    """
    def __init__(self, app_info: ApplicationInfo, **properties):
        """
        :param app_info: ApplicationInfo obj with data about related app file
        :param properties: additional Gtk.ListBoxRow properties
        """
        super().__init__(app_info, **properties)
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.event_box.add(self.box)
        self.get_style_context().add_class('app_entry')
        self._setup_menu()

        self.icon = Gtk.Image()
        self.label = LimitedWidthLabel()
        self.box.pack_start(self.icon, False, False, 5)
        self.box.pack_start(self.label, False, False, 5)

        self.update_contents()

    def _has_favorite_sibling(self):
        """
        Helper function, check if any other related Application Rows are
        for Favorites
        """
        for entry in self.app_info.entries:
            if isinstance(entry, FavoritesAppEntry):
                return True
        return False

    def _setup_menu(self):
        """
        Setup right click menu: currently only one option, add to favorites.
        """
        self.add_menu_item = Gtk.CheckMenuItem(label='Add to favorites')
        self.add_menu_item.connect('activate', self._add_to_favorites)
        self.menu.add(self.add_menu_item)
        self.menu.show_all()

    def show_menu(self, widget, event):
        """
        Show right click menu. For ephemeral VMs (class DispVM with a template
        set) the menu is inactive. If the current App is already added to
        favorites, the "add to favorites" option is checked and inactive.
        """
        if getattr(self.get_parent(), 'ephemeral_vm', False):
            self.add_menu_item.set_active(False)
            self.add_menu_item.set_sensitive(False)
        else:
            is_favorite = self._has_favorite_sibling()
            self.add_menu_item.set_active(is_favorite)
            self.add_menu_item.set_sensitive(not is_favorite)
        super().show_menu(widget, event)

    def update_contents(self):
        """Update icon and app name."""
        self.icon.set_from_pixbuf(
            load_icon(self.app_info.app_icon, Gtk.IconSize.LARGE_TOOLBAR))
        self.label.set_label(self.app_info.app_name)
        self.show_all()

    def _add_to_favorites(self, *_args, **_kwargs):
        """
        "Add to favorites" action: sets appropriate VM feature
        """
        target_vm = self.app_info.vm
        if not target_vm:
            target_vm = self.app_info.qapp.domains[
                self.app_info.qapp.local_name]

        current_feature = target_vm.features.get(
            constants.FAVORITES_FEATURE, '').split(' ')

        if self.app_info.entry_name in current_feature:
            return
        current_feature.append(self.app_info.entry_name)
        target_vm.features[constants.FAVORITES_FEATURE] \
            = ' '.join(current_feature)


class FavoritesAppEntry(AppEntry):
    """
    Application Gtk.ListBoxRow for use in Favorites page.
    Favorites are stored in VM's feature, name of which is stored in
    constants.py, as a space-separated list containing a subset of menu-items
    feature.
    """
    def __init__(self, app_info: ApplicationInfo, **properties):
        super().__init__(app_info, **properties)
        self.get_style_context().add_class('favorite_entry')
        self.grid = Gtk.Grid()
        self.event_box.add(self.grid)
        self.remove_item = Gtk.MenuItem(label='Remove from favorites')
        self.remove_item.connect('activate', self._remove_from_favorites)
        self.menu.add(self.remove_item)
        self.menu.show_all()

        self.app_label = LimitedWidthLabel()
        self.vm_label = Gtk.Label()
        self.app_icon = Gtk.Image()
        self.vm_icon = Gtk.Image()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(self.vm_icon, False, False, 5)
        box.pack_start(self.vm_label, False, False, 5)
        self.vm_label.get_style_context().add_class('favorite_vm_name')
        self.app_label.get_style_context().add_class('favorite_app_name')
        self.app_label.set_halign(Gtk.Align.START)

        self.grid.attach(self.app_icon, 0, 0, 1, 2)
        self.grid.attach(self.app_label, 1, 0, 1, 1)
        self.grid.attach(box, 1, 1, 1, 1)

        self.update_contents()

    def update_contents(self):
        """Update application and VM icons and application and vm names"""
        vm_icon = load_icon(self.app_info.vm_icon, Gtk.IconSize.LARGE_TOOLBAR)
        self.vm_icon.set_from_pixbuf(vm_icon)

        app_icon = load_icon(self.app_info.app_icon, Gtk.IconSize.DIALOG)
        self.app_icon.set_from_pixbuf(app_icon)

        if self.app_info.disposable:
            self.vm_label.set_label(
                'new Disposable VM from ' + str(self.app_info.vm))
        elif self.app_info.vm:
            self.vm_label.set_label(str(self.app_info.vm))
        else:
            self.vm_label.set_label(str(self.app_info.qapp.local_name))
        self.app_label.set_label(str(self.app_info.app_name))
        self.show_all()

    def _remove_from_favorites(self, *_args, **_kwargs):
        """Remove from favorites, that is, from an appropriate VM
        feature"""
        vm = self.app_info.vm or self.app_info.qapp.domains[
            self.app_info.qapp.local_name]
        current_feature = vm.features.get(
            constants.FAVORITES_FEATURE, '').split(' ')

        try:
            current_feature.remove(self.app_info.entry_name)
        except ValueError:
            logger.info('Failed to remove %s from vm favorites for vm %s: '
                        'favorites did not contain %s',
                        self.app_info.entry_name, str(vm),
                        self.app_info.entry_name)
            self.get_parent().remove(self)
            return
        vm.features[constants.FAVORITES_FEATURE] = ' '.join(current_feature)
