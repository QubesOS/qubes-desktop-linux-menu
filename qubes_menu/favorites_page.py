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
Qubes App Menu favorites page and related widgets.
"""
import logging

import qubesadmin.events
from .desktop_file_manager import DesktopFileManager
from .app_widgets import AppEntry, FavoritesAppEntry
from .vm_manager import VMManager
from .utils import load_icon, read_settings, write_settings
from . import constants

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

logger = logging.getLogger('qubes-appmenu')

LIST_WHITE_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.LIST_WHITE, Gtk.IconSize.LARGE_TOOLBAR)
)
    
LIST_BLACK_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.LIST_BLACK, Gtk.IconSize.LARGE_TOOLBAR)
)

GRID_WHITE_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.GRID_WHITE, Gtk.IconSize.LARGE_TOOLBAR)
)

GRID_BLACK_ICON = Gtk.Image.new_from_pixbuf(
    load_icon(constants.GRID_BLACK, Gtk.IconSize.LARGE_TOOLBAR)
)

class FavoritesPage:
    """
    Helper class for managing the entirety of Favorites menu page.
    """
    def __init__(self, qapp: qubesadmin.Qubes, builder: Gtk.Builder,
                 desktop_file_manager: DesktopFileManager,
                 dispatcher: qubesadmin.events.EventsDispatcher,
                 vm_manager: VMManager):
        self.qapp = qapp
        self.desktop_file_manager = desktop_file_manager
        self.dispatcher = dispatcher
        self.vm_manager = vm_manager

        self.fav_apps_view: Gtk.Viewport = builder.get_object('fav_view_port')
        
        self.fav_apps_layout = read_settings(constants.FAVORITE_APPS_LAYOUT)

        self.fav_layout_toggle: Gtk.Button = builder.get_object('fav_layout_toggle')
        
        self.fav_layout_toggle.set_image(LIST_WHITE_ICON)\
            if self.fav_apps_layout == constants.LIST \
                else self.fav_layout_toggle.set_image(GRID_WHITE_ICON)

        self.fav_layout_toggle.connect('clicked', self._toggle_layout)
        self.fav_layout_toggle.connect('enter-notify-event', self._enter_layout_button)
        self.fav_layout_toggle.connect('leave-notify-event', self._leave_layout_button)

        self.app_grid: Gtk.FlowBox = Gtk.FlowBox()
        self.app_grid.get_style_context().add_class('left_pane')
        
        self.app_list: Gtk.ListBox = Gtk.ListBox()
        self.app_list.get_style_context().add_class('left_pane')
        
        self.app_list.connect('row-activated', self._app_clicked)
        
        self.app_list.set_sort_func(
            lambda x, y: x.app_info.app_name > y.app_info.app_name)
        
        self.app_list.show_all()
        self.app_list.invalidate_sort()
        self.app_list.set_selection_mode(Gtk.SelectionMode.NONE)
        
        
        self.fav_apps_view.add(self.app_list)\
            if self.fav_apps_layout == constants.LIST \
                else self.fav_apps_view.add(self.app_grid)

        self.desktop_file_manager.register_callback(self._app_info_callback)

        self.dispatcher.add_handler(
            f'domain-feature-set:{constants.FAVORITES_FEATURE}',
            self._feature_set)
        self.dispatcher.add_handler('domain-add', self._domain_added)
        self.dispatcher.add_handler('domain-delete', self._domain_deleted)

    def _toggle_layout(self, *args, **kwargs):
        if self.fav_apps_layout == constants.LIST:
            self.fav_apps_view.remove(self.app_list)
            self.fav_apps_view.add(self.app_grid)

            self.fav_layout_toggle.set_image(GRID_WHITE_ICON)
            
            self.fav_apps_layout = constants.GRID
            write_settings(constants.FAVORITE_APPS_LAYOUT, constants.GRID)
            
        elif self.fav_apps_layout == constants.GRID:
            self.fav_apps_view.remove(self.app_grid)
            self.fav_apps_view.add(self.app_list)

            self.fav_layout_toggle.set_image(LIST_WHITE_ICON)

            self.fav_apps_layout = constants.LIST
            write_settings(constants.FAVORITE_APPS_LAYOUT, constants.LIST)

    def _enter_layout_button(self, *args, **kwargs):
        current_img = self.fav_layout_toggle.get_image()

        if (current_img == LIST_WHITE_ICON):
            self.fav_layout_toggle.set_image(LIST_BLACK_ICON)

        elif (current_img == GRID_WHITE_ICON):
            self.fav_layout_toggle.set_image(GRID_BLACK_ICON)

    def _leave_layout_button(self, *args, **kwargs):
        current_img = self.fav_layout_toggle.get_image()

        if (current_img == LIST_BLACK_ICON):
            self.fav_layout_toggle.set_image(LIST_WHITE_ICON)

        elif (current_img == GRID_BLACK_ICON):
            self.fav_layout_toggle.set_image(GRID_WHITE_ICON)

    def _load_vms_favorites(self, vm):
        """
        Load favorites for all existing VMs, based on VM feature specified in
        constants.py file.
        """
        if isinstance(vm, str):
            try:
                vm = self.qapp.domains[vm]
            except KeyError:
                return
        favorites = vm.features.get(constants.FAVORITES_FEATURE, '')
        favorites = favorites.split(' ')

        is_local_vm = (vm.name == self.qapp.local_name)

        for app_info in self.desktop_file_manager.get_app_infos():
            if (not is_local_vm and app_info.vm == vm)\
                    or (is_local_vm and not app_info.vm):
                if app_info.entry_name in favorites:
                    self._add_from_app_info(app_info)
        self.app_list.invalidate_sort()
        self.app_list.show_all()

    def _app_info_callback(self, app_info):
        """Callback to be executed on every newly loaded ApplicationInfo."""
        if app_info.vm:
            vm = app_info.vm
        else:
            vm = app_info.qapp.domains[app_info.qapp.local_name]

        feature = vm.features.get(constants.FAVORITES_FEATURE, '').split(' ')
        if app_info.entry_name in feature:
            self._add_from_app_info(app_info)

    def _add_from_app_info(self, app_info):
        entry = FavoritesAppEntry(app_info, self.vm_manager)
        app_info.entries.append(entry)
        self.app_list.add(entry)

    @staticmethod
    def _app_clicked(_widget, row: AppEntry):
        row.run_app(row.app_info.vm)

    # def _feature_deleted(self, vm, _event, _feature, *_args, **_kwargs):
    #     """Callback to be executed when a VM feature is deleted, and also
    #     used for loading favorites when VM feature is changed."""
    #     try:
    #         if str(vm) == self.qapp.local_name:
    #             vm = None
    #         for child in self.app_list.get_children():
    #             if str(child.app_info.vm) == str(vm):
    #                 child.app_info.entries.remove(child)
    #                 self.app_list.remove(child)
    #         self.app_list.invalidate_sort()
    #     except Exception as ex:  # pylint: disable=broad-except
    #         logger.warning(
    #             'Encountered problem removing favorite entry: %s', repr(ex))

    def _feature_set(self, vm, event, feature, *_args, **_kwargs):
        """When VM feature specified in constants.py is changed, all existing
        favorites menu entries for this VM will be removed and then loaded
        afresh from the feature."""
        old_fav = _kwargs['oldvalue'].split(' ') if _kwargs['oldvalue'] else None
        new_fav = _kwargs['value'].split(' ')
        
        # Remove a favorite app
        if old_fav and len(old_fav) > len(new_fav) or new_fav == ['']:
            remove_fav = set(old_fav) - set(new_fav)
            
            for child in self.app_list.get_children():
                if str(child.app_info.vm) == str(vm) \
                    and child.app_info.entry_name in remove_fav:
                    child.app_info.entries.remove(child)
                    self.app_list.remove(child)
                    self.app_list.show_all()
                    break
            
        # Add a favorite app
        else:
            new_fav = set(new_fav) - set(old_fav) if old_fav else new_fav
            for app_info in self.desktop_file_manager.get_app_infos():
                if str(app_info.vm) == str(vm) \
                    and app_info.entry_name in new_fav:
                    self._add_from_app_info(app_info)
                    break

        

    def _domain_added(self, _submitter, _event, vm, **_kwargs):
        """On a newly created domain, load all favorites from features
        (the VM might have been restored from backup with features already
        there)"""
        self._load_vms_favorites(vm)

    def _domain_deleted(self, _submitter, event, vm, **_kwargs):
        """On domain delete, all related features should be removed."""
        self._feature_deleted(vm, event, None)
